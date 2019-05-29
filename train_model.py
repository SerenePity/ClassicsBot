import robotic_roman
import sys

robot = robotic_roman.RoboticRoman()
robot.train_model(sys.argv[1], sys.argv[2])