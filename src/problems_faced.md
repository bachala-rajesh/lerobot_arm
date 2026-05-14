1. timing issue in joint trajectory message
2. after adding namespace to the robot, the moveit2 was not working because of rviz2 topics and the movegroup namespace. 
    two things to be done in the rviz2 config file moveit.rviz: 
        1. the namespace need to be manually added to the topic names
        2. need to add 
            Move Group Namespace: follower
