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
        

        