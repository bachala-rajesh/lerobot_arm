#!/usr/bin/env python3
  import rclpy
  from rclpy.node import Node
  from moveit_msgs.msg import CollisionObject, PlanningScene
  from shape_msgs.msg import SolidPrimitive
  from geometry_msgs.msg import Pose


  class SceneObjectsPublisher(Node):
      def __init__(self):
          super().__init__('scene_objects_publisher')
          self.pub = self.create_publisher(PlanningScene,
  '/follower/monitored_planning_scene', 1)
          # Publish once after a short delay so move_group is ready
          self.timer = self.create_timer(3.0, self.publish_scene)

      def publish_scene(self):
          self.timer.cancel()

          planning_scene = PlanningScene()
          planning_scene.is_diff = True

          # --- Floor ---
          floor = CollisionObject()
          floor.id = 'floor'
          floor.header.frame_id = 'world'
          box = SolidPrimitive()
          box.type = SolidPrimitive.BOX
          box.dimensions = [3.0, 3.0, 0.01]   # 3m wide, 1cm thick
          pose = Pose()
          pose.position.z = 0.0               # at world origin (z=0)
          pose.orientation.w = 1.0
          floor.primitives = [box]
          floor.primitive_poses = [pose]
          floor.operation = CollisionObject.ADD

          # --- Table ---
          table = CollisionObject()
          table.id = 'table'
          table.header.frame_id = 'world'
          t_box = SolidPrimitive()
          t_box.type = SolidPrimitive.BOX
          t_box.dimensions = [1.0, 1.0, 1.0]  # matches scene.urdf table box
          t_pose = Pose()
          t_pose.position.z = 0.5             # table_link is at z=0.5 in world
          t_pose.orientation.w = 1.0
          table.primitives = [t_box]
          table.primitive_poses = [t_pose]
          table.operation = CollisionObject.ADD

          planning_scene.world.collision_objects = [floor, table]
          self.pub.publish(planning_scene)
          self.get_logger().info('Published floor and table collision objects')


  def main():
      rclpy.init()
      rclpy.spin(SceneObjectsPublisher())
      rclpy.shutdown()
