"""SLAM wrapper node — integrates KISS-ICP with Aerostack2."""

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from sensor_msgs.msg import PointCloud2, PointField
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster

from kiss_icp.kiss_icp import KissICP
from kiss_icp.config import KISSConfig


def pointcloud2_to_numpy(msg: PointCloud2) -> np.ndarray:
    """Convert ROS2 PointCloud2 to Nx3 numpy array (x, y, z only)."""
    import struct

    # Find xyz field offsets
    field_map = {f.name: f for f in msg.fields}
    if 'x' not in field_map or 'y' not in field_map or 'z' not in field_map:
        return np.zeros((0, 3), dtype=np.float64)

    ox = field_map['x'].offset
    oy = field_map['y'].offset
    oz = field_map['z'].offset
    point_step = msg.point_step
    data = msg.data

    n_points = msg.width * msg.height
    points = np.zeros((n_points, 3), dtype=np.float64)

    for i in range(n_points):
        base = i * point_step
        points[i, 0] = struct.unpack_from('f', data, base + ox)[0]
        points[i, 1] = struct.unpack_from('f', data, base + oy)[0]
        points[i, 2] = struct.unpack_from('f', data, base + oz)[0]

    # Filter out NaN and Inf
    valid = np.isfinite(points).all(axis=1)
    return points[valid]


def numpy_to_pointcloud2(points: np.ndarray, header) -> PointCloud2:
    """Convert Nx3 numpy array to ROS2 PointCloud2."""
    import struct

    msg = PointCloud2()
    msg.header = header
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

    points_f32 = points.astype(np.float32)
    msg.data = points_f32.tobytes()
    return msg


def pose_matrix_to_odom(pose: np.ndarray, header, child_frame: str) -> Odometry:
    """Convert 4x4 pose matrix to nav_msgs/Odometry."""
    from scipy.spatial.transform import Rotation

    odom = Odometry()
    odom.header = header
    odom.child_frame_id = child_frame

    # Translation
    odom.pose.pose.position.x = float(pose[0, 3])
    odom.pose.pose.position.y = float(pose[1, 3])
    odom.pose.pose.position.z = float(pose[2, 3])

    # Rotation (matrix to quaternion)
    rot = Rotation.from_matrix(pose[:3, :3])
    q = rot.as_quat()  # [x, y, z, w]
    odom.pose.pose.orientation.x = float(q[0])
    odom.pose.pose.orientation.y = float(q[1])
    odom.pose.pose.orientation.z = float(q[2])
    odom.pose.pose.orientation.w = float(q[3])

    return odom


def pose_matrix_to_tf(pose: np.ndarray, stamp, parent_frame: str,
                      child_frame: str) -> TransformStamped:
    """Convert 4x4 pose matrix to TF transform."""
    from scipy.spatial.transform import Rotation

    t = TransformStamped()
    t.header.stamp = stamp
    t.header.frame_id = parent_frame
    t.child_frame_id = child_frame

    t.transform.translation.x = float(pose[0, 3])
    t.transform.translation.y = float(pose[1, 3])
    t.transform.translation.z = float(pose[2, 3])

    rot = Rotation.from_matrix(pose[:3, :3])
    q = rot.as_quat()
    t.transform.rotation.x = float(q[0])
    t.transform.rotation.y = float(q[1])
    t.transform.rotation.z = float(q[2])
    t.transform.rotation.w = float(q[3])

    return t


class SlamWrapperNode(Node):
    """ROS 2 node wrapping KISS-ICP for LiDAR-based 3D SLAM."""

    def __init__(self):
        super().__init__('slam_wrapper')

        # Declare parameters
        self.declare_parameter('point_cloud_topic', 'sensor_measurements/lidar_0/points')
        self.declare_parameter('slam_backend', 'kiss_icp')
        self.declare_parameter('min_range', 0.5)
        self.declare_parameter('max_range', 100.0)
        self.declare_parameter('voxel_size', 1.0)
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_link')

        # Read parameters
        pc_topic = self.get_parameter('point_cloud_topic').value
        backend = self.get_parameter('slam_backend').value
        min_range = self.get_parameter('min_range').value
        max_range = self.get_parameter('max_range').value
        voxel_size = self.get_parameter('voxel_size').value
        self.map_frame = self.get_parameter('map_frame').value
        self.odom_frame = self.get_parameter('odom_frame').value
        self.base_frame = self.get_parameter('base_frame').value

        self.get_logger().info(f'SLAM backend: {backend}')
        self.get_logger().info(f'Subscribing to: {pc_topic}')
        self.get_logger().info(f'Range filter: [{min_range}, {max_range}]m')
        self.get_logger().info(f'Voxel size: {voxel_size}m')

        # Initialize KISS-ICP
        config = KISSConfig()
        config.data.min_range = min_range
        config.data.max_range = max_range
        config.data.deskew = False  # Gazebo provides undistorted clouds
        config.mapping.voxel_size = voxel_size
        self.kiss_icp = KissICP(config)

        # QoS for sensor data
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=5)

        # Subscriber
        self.pc_sub = self.create_subscription(
            PointCloud2, pc_topic, self.point_cloud_callback, sensor_qos)

        # Publishers
        self.odom_pub = self.create_publisher(Odometry, 'slam/odom', 10)
        self.map_cloud_pub = self.create_publisher(PointCloud2, 'slam/map_cloud', 10)

        # TF broadcaster
        self.tf_broadcaster = TransformBroadcaster(self)

        self.msg_count = 0
        self.get_logger().info('SlamWrapperNode initialized — waiting for point cloud data...')

    def point_cloud_callback(self, msg: PointCloud2):
        """Process incoming point cloud through KISS-ICP."""
        self.msg_count += 1

        # Convert to numpy
        points = pointcloud2_to_numpy(msg)
        if len(points) == 0:
            return

        # Run KISS-ICP registration
        timestamps = np.zeros(len(points))  # Gazebo clouds are synchronous
        self.kiss_icp.register_frame(points, timestamps)

        # Get current pose (4x4 matrix)
        pose = self.kiss_icp.last_pose

        # Get namespace for frame prefixing
        ns = self.get_namespace().strip('/')
        map_frame = f'{ns}/{self.map_frame}' if ns else self.map_frame
        odom_frame = f'{ns}/{self.odom_frame}' if ns else self.odom_frame
        base_frame = f'{ns}/{self.base_frame}' if ns else self.base_frame

        stamp = msg.header.stamp

        # Publish odometry
        odom_header = msg.header
        odom_header.frame_id = map_frame
        odom_msg = pose_matrix_to_odom(pose, odom_header, base_frame)
        self.odom_pub.publish(odom_msg)

        # Publish map cloud (local map from KISS-ICP) — every 10th frame to save bandwidth
        if self.msg_count % 10 == 1:
            local_map_points = self.kiss_icp.local_map.point_cloud()
            map_header = msg.header
            map_header.frame_id = map_frame
            map_cloud_msg = numpy_to_pointcloud2(local_map_points, map_header)
            self.map_cloud_pub.publish(map_cloud_msg)

        # Log periodically
        if self.msg_count % 10 == 1:
            pos = pose[:3, 3]
            self.get_logger().info(
                f'Frame #{self.msg_count}: {len(points)} pts, '
                f'pose=[{pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}], '
                f'map_size={self.kiss_icp.local_map.point_cloud().shape[0]}')


def main(args=None):
    rclpy.init(args=args)
    node = SlamWrapperNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
