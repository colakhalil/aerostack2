"""
as2_3d_map_manager — 3D Map Manager Node for Aerostack2

Subscribes to SLAM point cloud, accumulates into a global voxel grid
using Open3D, publishes the downsampled map, and provides a save_map service.
"""
import os
from datetime import datetime

import numpy as np
import open3d as o3d
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import PointCloud2, PointField
from std_srvs.srv import Trigger


def pointcloud2_to_numpy(msg: PointCloud2) -> np.ndarray:
    """Convert ROS2 PointCloud2 (xyz float32) to Nx3 numpy array."""
    field_map = {f.name: f for f in msg.fields}
    if 'x' not in field_map or 'y' not in field_map or 'z' not in field_map:
        return np.zeros((0, 3), dtype=np.float64)

    ox = field_map['x'].offset
    oy = field_map['y'].offset
    oz = field_map['z'].offset
    point_step = msg.point_step
    n_points = msg.width * msg.height

    # Vectorized parsing — much faster than per-point struct.unpack
    data = np.frombuffer(msg.data, dtype=np.uint8).reshape(n_points, point_step)
    x = np.frombuffer(data[:, ox:ox+4].tobytes(), dtype=np.float32)
    y = np.frombuffer(data[:, oy:oy+4].tobytes(), dtype=np.float32)
    z = np.frombuffer(data[:, oz:oz+4].tobytes(), dtype=np.float32)
    points = np.column_stack((x, y, z)).astype(np.float64)

    valid = np.isfinite(points).all(axis=1)
    return points[valid]


def numpy_to_pointcloud2(points: np.ndarray, stamp, frame_id: str) -> PointCloud2:
    """Convert Nx3 numpy array to ROS2 PointCloud2."""
    msg = PointCloud2()
    msg.header.stamp = stamp
    msg.header.frame_id = frame_id
    msg.height = 1
    msg.width = len(points)
    msg.fields = [
        PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
        PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
        PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
    ]
    msg.is_bigendian = False
    msg.point_step = 12
    msg.row_step = 12 * len(points)
    msg.is_dense = True
    msg.data = points.astype(np.float32).tobytes()
    return msg


class MapManagerNode(Node):
    def __init__(self):
        super().__init__('map_manager_node')

        # Parameters
        self.declare_parameter('input_topic', 'slam/map_cloud')
        self.declare_parameter('voxel_size', 0.1)
        self.declare_parameter('max_points', 0)
        self.declare_parameter('output_dir', '~/aerostack2_maps')
        self.declare_parameter('global_frame', 'earth')
        self.declare_parameter('publish_interval', 5.0)

        input_topic = self.get_parameter('input_topic').value
        self.voxel_size = self.get_parameter('voxel_size').value
        self.max_points = self.get_parameter('max_points').value
        self.global_frame = self.get_parameter('global_frame').value
        publish_interval = self.get_parameter('publish_interval').value

        self.get_logger().info(f'input_topic: {input_topic}')
        self.get_logger().info(f'voxel_size: {self.voxel_size} m')
        self.get_logger().info(f'max_points: {self.max_points} (0=unlimited)')
        self.get_logger().info(f'global_frame: {self.global_frame}')
        self.get_logger().info(f'publish_interval: {publish_interval} s')

        # Global accumulated map (Open3D)
        self.global_map = o3d.geometry.PointCloud()
        self.cloud_count = 0

        # QoS
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            depth=5
        )

        self.subscription = self.create_subscription(
            PointCloud2, input_topic, self._cloud_callback, qos)

        self.map_pub = self.create_publisher(
            PointCloud2, 'map_manager/accumulated_map', qos)

        # Publish accumulated map periodically (not every callback — too expensive)
        self.publish_timer = self.create_timer(publish_interval, self._publish_map)

        # Save map service
        self.output_dir = os.path.expanduser(
            self.get_parameter('output_dir').value)
        self.save_srv = self.create_service(
            Trigger, 'map_manager/save_map', self._save_map_callback)

        self.get_logger().info(f'output_dir: {self.output_dir}')
        self.get_logger().info('Map Manager Node started — waiting for point clouds...')
        self.get_logger().info('  Save map: ros2 service call /drone0/map_manager/save_map std_srvs/srv/Trigger')

    def _cloud_callback(self, msg: PointCloud2):
        points = pointcloud2_to_numpy(msg)
        if len(points) == 0:
            return

        self.cloud_count += 1

        # Add new points to global map
        new_cloud = o3d.geometry.PointCloud()
        new_cloud.points = o3d.utility.Vector3dVector(points)
        self.global_map += new_cloud

        # Voxel downsample to keep map manageable
        if self.voxel_size > 0:
            self.global_map = self.global_map.voxel_down_sample(self.voxel_size)

        # Enforce max points limit
        if self.max_points > 0 and len(self.global_map.points) > self.max_points:
            indices = np.random.choice(
                len(self.global_map.points), self.max_points, replace=False)
            self.global_map = self.global_map.select_by_index(indices)

        map_size = len(self.global_map.points)
        if self.cloud_count % 10 == 1:
            self.get_logger().info(
                f'Cloud #{self.cloud_count}: +{len(points)} pts | '
                f'Map: {map_size} pts (after voxel {self.voxel_size}m)')

    def _publish_map(self):
        map_size = len(self.global_map.points)
        if map_size == 0:
            return

        points = np.asarray(self.global_map.points)
        stamp = self.get_clock().now().to_msg()
        cloud_msg = numpy_to_pointcloud2(points, stamp, self.global_frame)
        self.map_pub.publish(cloud_msg)
        self.get_logger().debug(f'Published accumulated map: {map_size} pts')

    def _save_map_callback(self, request, response):
        map_size = len(self.global_map.points)
        if map_size == 0:
            response.success = False
            response.message = 'Map is empty — nothing to save'
            self.get_logger().warn(response.message)
            return response

        os.makedirs(self.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        pcd_path = os.path.join(self.output_dir, f'map_{timestamp}.pcd')
        ply_path = os.path.join(self.output_dir, f'map_{timestamp}.ply')

        o3d.io.write_point_cloud(pcd_path, self.global_map)
        o3d.io.write_point_cloud(ply_path, self.global_map)

        msg = (f'Saved {map_size} points → {pcd_path} + {ply_path}')
        self.get_logger().info(msg)
        response.success = True
        response.message = msg
        return response


def main(args=None):
    rclpy.init(args=args)
    node = MapManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        map_size = len(node.global_map.points)
        node.get_logger().info(
            f'Shutting down — {node.cloud_count} clouds received, '
            f'final map: {map_size} pts')
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
