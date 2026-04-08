"""
map_merger_node — Merges accumulated maps from multiple drones into a single global map.

Subscribes to /droneN/map_manager/accumulated_map for each drone,
merges them with voxel downsampling, and publishes /merged_map.
"""
import numpy as np
import open3d as o3d
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import PointCloud2, PointField
from std_srvs.srv import Trigger
import os
from datetime import datetime


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


class MapMergerNode(Node):
    def __init__(self):
        super().__init__('map_merger_node')

        # Parameters
        self.declare_parameter('drone_namespaces', ['drone0', 'drone1'])
        self.declare_parameter('voxel_size', 0.1)
        self.declare_parameter('publish_interval', 5.0)
        self.declare_parameter('output_frame', 'earth')
        self.declare_parameter('output_dir', '~/aerostack2_maps')

        self.drone_namespaces = self.get_parameter('drone_namespaces').value
        self.voxel_size = self.get_parameter('voxel_size').value
        publish_interval = self.get_parameter('publish_interval').value
        self.output_frame = self.get_parameter('output_frame').value

        self.get_logger().info(f'Drone namespaces: {self.drone_namespaces}')
        self.get_logger().info(f'Voxel size: {self.voxel_size} m')
        self.get_logger().info(f'Output frame: {self.output_frame}')
        self.get_logger().info(f'Publish interval: {publish_interval} s')

        # Store latest map from each drone
        self.drone_maps = {ns: None for ns in self.drone_namespaces}

        # QoS
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            depth=5
        )

        # Subscribe to each drone's accumulated_map
        self.subscriptions_list = []
        for ns in self.drone_namespaces:
            topic = f'/{ns}/map_manager/accumulated_map'
            sub = self.create_subscription(
                PointCloud2, topic,
                lambda msg, drone_ns=ns: self._map_callback(msg, drone_ns),
                qos)
            self.subscriptions_list.append(sub)
            self.get_logger().info(f'  Subscribing to: {topic}')

        # Publisher for merged map
        self.merged_pub = self.create_publisher(
            PointCloud2, '/merged_map', qos)

        # Periodic merge + publish
        self.publish_timer = self.create_timer(publish_interval, self._merge_and_publish)

        # Save merged map service
        self.output_dir = os.path.expanduser(
            self.get_parameter('output_dir').value)
        self.save_srv = self.create_service(
            Trigger, '/map_merger/save_map', self._save_map_callback)

        self.merged_map = o3d.geometry.PointCloud()

        self.get_logger().info('Map Merger Node started — waiting for drone maps...')
        self.get_logger().info(f'  Save merged: ros2 service call /map_merger/save_map std_srvs/srv/Trigger')

    def _map_callback(self, msg: PointCloud2, drone_ns: str):
        points = pointcloud2_to_numpy(msg)
        if len(points) == 0:
            return

        cloud = o3d.geometry.PointCloud()
        cloud.points = o3d.utility.Vector3dVector(points)
        self.drone_maps[drone_ns] = cloud

    def _merge_and_publish(self):
        # Collect all available drone maps
        available = {ns: cloud for ns, cloud in self.drone_maps.items() if cloud is not None}
        if not available:
            return

        # Merge all drone maps
        merged = o3d.geometry.PointCloud()
        for cloud in available.values():
            merged += cloud

        # Voxel downsample
        if self.voxel_size > 0 and len(merged.points) > 0:
            merged = merged.voxel_down_sample(self.voxel_size)

        self.merged_map = merged
        map_size = len(merged.points)

        # Publish
        points = np.asarray(merged.points)
        stamp = self.get_clock().now().to_msg()
        cloud_msg = numpy_to_pointcloud2(points, stamp, self.output_frame)
        self.merged_pub.publish(cloud_msg)

        drone_info = ', '.join(f'{ns}={len(c.points)}' for ns, c in available.items())
        self.get_logger().info(
            f'Merged map: {map_size} pts from {len(available)} drones ({drone_info})')

    def _save_map_callback(self, request, response):
        map_size = len(self.merged_map.points)
        if map_size == 0:
            response.success = False
            response.message = 'Merged map is empty — nothing to save'
            self.get_logger().warn(response.message)
            return response

        os.makedirs(self.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        pcd_path = os.path.join(self.output_dir, f'merged_map_{timestamp}.pcd')
        ply_path = os.path.join(self.output_dir, f'merged_map_{timestamp}.ply')

        o3d.io.write_point_cloud(pcd_path, self.merged_map)
        o3d.io.write_point_cloud(ply_path, self.merged_map)

        msg = f'Saved merged map {map_size} points → {pcd_path} + {ply_path}'
        self.get_logger().info(msg)
        response.success = True
        response.message = msg
        return response


def main(args=None):
    rclpy.init(args=args)
    node = MapMergerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        map_size = len(node.merged_map.points)
        node.get_logger().info(f'Shutting down — merged map: {map_size} pts')
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
