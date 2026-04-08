#include <string>
#include <memory>

#include "as2_core/node.hpp"
#include "sensor_msgs/msg/point_cloud2.hpp"

class SlamWrapperNode : public as2::Node
{
public:
  explicit SlamWrapperNode(const rclcpp::NodeOptions & options = rclcpp::NodeOptions())
  : as2::Node("slam_wrapper", options)
  {
    // Declare parameters with defaults
    this->declare_parameter<std::string>("point_cloud_topic", "sensor_measurements/lidar_0/points");
    this->declare_parameter<std::string>("slam_backend", "kiss_icp");

    // Read parameters
    std::string pc_topic = this->get_parameter("point_cloud_topic").as_string();
    std::string backend = this->get_parameter("slam_backend").as_string();

    RCLCPP_INFO(this->get_logger(), "SLAM backend: %s", backend.c_str());
    RCLCPP_INFO(this->get_logger(), "Subscribing to: %s", pc_topic.c_str());

    // Subscribe to point cloud
    pc_sub_ = this->create_subscription<sensor_msgs::msg::PointCloud2>(
      pc_topic, rclcpp::SensorDataQoS(),
      std::bind(&SlamWrapperNode::point_cloud_callback, this, std::placeholders::_1));

    RCLCPP_INFO(this->get_logger(), "SlamWrapperNode initialized — waiting for point cloud data...");
  }

private:
  void point_cloud_callback(const sensor_msgs::msg::PointCloud2::SharedPtr msg)
  {
    msg_count_++;
    if (msg_count_ % 10 == 1) {
      RCLCPP_INFO(
        this->get_logger(),
        "Received point cloud #%zu: %u points, frame=%s",
        msg_count_, msg->width * msg->height, msg->header.frame_id.c_str());
    }
  }

  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr pc_sub_;
  size_t msg_count_ = 0;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<SlamWrapperNode>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
