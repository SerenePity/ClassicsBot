import sys

import robotic_roman

robot = robotic_roman.RoboticRoman()
robot.train_model(sys.argv[1], sys.argv[2])
