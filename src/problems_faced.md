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
        

        