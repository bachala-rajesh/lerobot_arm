1. timing issue in joint trajectory message
2. after adding namespace to the robot, the moveit2 was not working because of rviz2 topics and the movegroup namespace. 
    two things to be done in the rviz2 config file moveit.rviz: 
        1. the namespace need to be manually added to the topic names
        2. need to add 
            Move Group Namespace: follower
3. oakd camera integration:
    a. tf frames - aprent and child frame issue
        - solved by creating a ros2 node that takes the data of all the april tags and then publishes tf frame between world and camera.
    b. 
4. pipecat version mismatch - tested in python 3.11 and deployed in python 3.10
    a. the async feature of stream is problematic.

5. AnyGrasp SDK install (conda env `anygrasp`, CUDA 12.6, torch cu126).
   Full step-by-step + all 9 problems & fixes in: src/setup_anygrasp.md
   Quick recall of the tricky ones:
       a. system CUDA 13.0 too new -> install cuda-toolkit 12.6 INSIDE conda env.
       b. env leaked ~/.local packages -> always run with PYTHONNOUSERSITE=1.
       c. MinkowskiEngine nvtx3.hpp clash w/ CUDA 12.6 -> swap in modern nvtx3 headers.
       d. modern nvtx dropped domain_thread_range -> stub ranges.hpp CUDF_FUNC_RANGE() to no-op.
       e. std::__to_address ambiguous -> sed-patch conda gcc shared_ptr_base.h (README hack, conda header).
       f. gsnet.so needs libcrypto.so.1.1 -> side-load openssl 1.1 libs via LD_LIBRARY_PATH.
       g. np.float removed -> pin numpy==1.23.5 (<1.24); install it LAST.
       h. graspnetAPI pulls deprecated sklearn -> SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True.
   For docker: patches c, d, e must be redone; .so must match docker python; license may need re-register.

        

6. 6DOF arm Gazebo ODE crash + controller config issues (dof_type:=dof_6)

   Problem A — ODE physics crash on spawn:
       Error: assertion "aabbBound >= dMinIntExact && aabbBound < dMaxIntExact" failed in collide() [collision_space.cpp:460]
       Cause: shoulder_link STL collision mesh physically overlaps base_link STL mesh at the joint
              connection. ODE handles box-box overlap fine but crashes on deep mesh-mesh interpenetration.
       Fix:   Replace shoulder_link collision with a box. All other links keep STL mesh collision.
              shoulder_link box: origin xyz="0.0194 0.0011 0.0068", size="0.050 0.040 0.1107"
       Note:  Tested all links one by one. Only shoulder_link causes crash. Root cause is mesh
              interpenetration at the shoulder_pan joint, not mesh size or vertex range.




    problem- B
        6A. right jaw moves under the influence of gravity. not mimicking the left jaw
        6B. the orientation is 90 degrees to the cockwise

7. MoveIt2 error: Joint 'right_jaw_slider_mimic' not found in model 'so101_arm'  [NOT SOLVED]

   Root cause:
       - 6DOF URDF has right_jaw_slider joint with <mimic joint="gripper" multiplier="-1"/>
       - Gazebo ros2_control plugin reads the mimic param and creates a hardware interface
         named right_jaw_slider_mimic (appends _mimic suffix)
       - This name is published in /follower/joint_states
       - MoveIt reads that topic, tries getJointModel("right_jaw_slider_mimic") → not in model → ERROR
       - Source confirmed: SO answer + ros2 topic echo showing right_jaw_slider_mimic in joint_states
       - Source file: gz_ros2_control plugin (ign_system.cpp line ~279)

   Temporary fix (applied):
       - Remove mimic params from right_jaw_slider block in:
         src/so101_description/urdf/ros2_control/sim_gazebo_so101_follower_ros2_control.urdf
         (remove lines: <param name="mimic">gripper</param> and <param name="multiplier">-1</param>)
       - Side effect: right jaw does NOT mirror left jaw in Gazebo simulation
         Grasp simulation will be asymmetric (only left jaw closes)

   Proper fix (not done):
       - Build gz_ros2_control from source
       - In ign_system.cpp, change the _mimic suffix to empty string ""
       - This preserves mimic behavior AND fixes MoveIt error


8. MoveIt octomap from sim OAK-D camera — point cloud / robot MISALIGNMENT (SIM, gz Fortress)

   Goal: feed the gz OAK-D point cloud (/oak/points) into MoveIt octomap for collision avoidance.
   Symptom: in RViz the octomap/cloud did NOT line up with the robot arm.
   Two independent root causes were found and fixed.

   --- Cause A: the arm had THREE conflicting world-pose numbers ---
       world -> follower_base_link was set in 3 places, all different:
         1. Gazebo spawn        : create -x 0 -y 0.40 -z 0.97 -Y -1.5708  (physical body)
         2. URDF world_joint     : origin 0 0 0                           (used by RViz + MoveIt)
         3. static_tf_follower_base : 0 0.25 0.47                         (a duplicate static TF)
       => RViz/MoveIt showed the arm at the origin while the real arm (and the camera-seen
          octomap) were on the table. Self-filter also failed.

       Fix — ONE source of truth = the URDF world_joint, selected by sim_mode:
         - so101_description/urdf/so101_arm_with_control.urdf.xacro: world_joint origin is
           conditional: sim_mode==gazebo -> 0 0.40 0.97 (+ yaw -1.5708 for dof_6);
           else -> 0 0 0 (REAL ROBOT SAFE default).
         - so101_bringup/launch/follower_gazebo.launch.py: spawn the arm at the ORIGIN
           (removed -x -y -z -Y); the pose now comes from the URDF (same trick as the camera).
         - so101_bringup/launch/moveit_server_sim_6dof.launch.py: build with
           .robot_description(mappings={"sim_mode":"gazebo","dof_type":"dof_6"}) so MoveIt reads
           the same table pose. (moveit_status=true still skips the ros2_control block.)
         - so101_description/launch/follower_description.launch.py: REMOVED
           static_tf_follower_base — it duplicated/conflicted with the URDF world_joint in ALL
           modes (real included). world_joint is now the single publisher of world->base.
       Verify: gazebo arm pose, TF world->follower_base_link, and RViz model all = 0,0.40,0.97.

   --- Cause B: gz publishes a WRONG camera_info -> depth cloud shifted ---
       gz Ignition rgbd_camera published camera_info whose K and P matrices kept the DEFAULT
       320x240 / 60deg intrinsics (fx=277, cx=160, cy=120) even though the depth image is
       640x480 / 71deg. depth_image_proc deprojects with the wrong principal point -> the whole
       cloud is shifted ~0.3-0.4 m. Verified: a cube at real (0,0,1.0) appeared in the cloud at
       (0.23,0.32,0.76); the offset predicted from the wrong K matched the measurement.

       Fix attempt 1 (partial): <lens><intrinsics> in the sensor SDF
         (fx=441, cx=320, cy=240) -> fixed K, but gz LEFT P at the default (277,160,120).
         depth_image_proc uses P (projection), NOT K -> still shifted.

       Fix (final): node oakd_camera/scripts/fix_camera_info.py
         - subscribes /oak/stereo/camera_info, sets P = [K | 0] (valid when no distortion),
           republishes /oak/stereo/camera_info_fixed; KEEPS the original timestamp so the
           depth image + camera_info still sync (no timing mismatch).
         - oakd_sim_pointcloud.launch.py: runs the fixer + remaps depth_image_proc
           camera_info -> /oak/stereo/camera_info_fixed.
       Result: cube cloud lands on (0,0,1.0); octomap perfectly aligned with the arm.

   Real robot notes:
       - sensors_3d.yaml (PointCloudOctomapUpdater on /oak/points, octomap_frame=world) is
         PORTABLE -> same config works on real.
       - camera_info fixer + table pose + spawn-at-origin are SIM-ONLY (gated by sim_mode) ->
         real robot untouched. Real depthai driver gives a correct camera_info.
       - On real, camera pose world->camera comes from the AprilTag node -> alignment quality
         depends on AprilTag calibration accuracy.
       - Real depth is 16UC1 (mm) -> needs ConvertMetric before depth_image_proc
         (already handled in oakd_camera_with_pointclouds.launch.py).
       - Requires ros-humble-moveit-ros-perception (provides the octomap updater plugins).
        

  9. VLM perception issue
    - The VLM prompt for scene description is not detailed enough to describe the multiple objects of same type in the scene
    - what if the scene is chnaged ?
    - the occluded object are not well recognized- the class is wrong
    - the results vary on call to call- need to set the temperature set
    



  10. the 6dof urdf has differetn axes convention and different rotating axes compared to the 5dof arm
    - some joints were rotating in the negative directions
    solution: corrected the axes of rotation by matching it with real robot axes rotation

    