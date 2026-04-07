# project_slam_gazebo

LiDAR tabanlı 3D SLAM + 3D mapping için Aerostack2 test/demo projesi.

Bu klasör AS2 core paketlerinden tamamen izoledir; yalnızca `as2_gazebo_assets`
ve ileride eklenecek `as2_slam_*` paketlerini **tüketir**.

## Yapı

- `config/` — simülasyon ve SLAM config dosyaları (JSON/YAML)
- `launch/` — birleşik launch dosyaları (ileride eklenecek)
- `worlds/` — proje-özel jinja dünya şablonları (ileride eklenecek)
- `rviz/` — RViz konfigürasyonları (ileride eklenecek)

## Faz 1.1 — Manuel Test

Şu anda sadece `config/slam_single.json` mevcut. Test için iki terminal:

### Terminal 1 — Gazebo + world
```bash
source /opt/ros/humble/setup.bash
source /home/halil/aerostack2/install/setup.bash
ros2 launch as2_gazebo_assets launch_simulation.py \
    simulation_config_file:=/home/halil/aerostack2/projects/project_slam_gazebo/config/slam_single.json
```

### Terminal 2 — Drone bridges
```bash
source /opt/ros/humble/setup.bash
source /home/halil/aerostack2/install/setup.bash
ros2 launch as2_gazebo_assets drone_bridges.py \
    simulation_config_file:=/home/halil/aerostack2/projects/project_slam_gazebo/config/slam_single.json \
    namespace:=drone0
```

### Terminal 3 — Doğrulama
```bash
ros2 topic list | grep drone0
ros2 topic hz /drone0/sensor_measurements/lidar_0/points
```

F1.2'de bu iki launch tek komuta birleşecek.
