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
        
