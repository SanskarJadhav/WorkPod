from ..common.settings import REWARD_FUNCTION, COLLISION_OBSTACLE, COLLISION_WALL, TUMBLE, SUCCESS, TIMEOUT, RESULTS_NUM
import numpy as np
import math

goal_dist_initial = 0

reward_function_internal = None

def get_reward(succeed, action_linear, action_angular, distance_to_goal, goal_angle, min_obstacle_distance):
    return reward_function_internal(succeed, action_linear, action_angular, distance_to_goal, goal_angle, min_obstacle_distance)

# MODIFICATION ON FRIDAY 29/08/24
# def get_reward_A(succeed, action_linear, action_angular, goal_dist, goal_angle, min_obstacle_dist):
#         # [-3.14, 0]
#         r_yaw = -1 * abs(goal_angle)

#         # [-4, 0]
#         r_vangular = -1 * (action_angular**2)

#         # [-1, 1]
#         r_distance = 5/goal_dist

#         # [-20, 0]
#         if min_obstacle_dist < 0.4:
#             r_obstacle = -5 + abs(action_angular) - action_linear
#         else:
#             r_obstacle = 0 + action_linear

#         # [-2 * (2.2^2), 0]
#         r_vlinear = -1 * ((1 - action_linear) ** 2)

#         r_diff = 2 * (abs(action_linear - (abs(action_angular)/2)) - 1)

#         reward = r_yaw + r_distance + r_obstacle + r_vlinear + r_vangular + r_diff - 1

#         if succeed == SUCCESS:
#             reward += 5000
#         elif succeed == COLLISION_OBSTACLE or succeed == COLLISION_WALL:
#             reward -= 2000
#         return float(reward)

# version27b
# def get_reward_A(succeed, action_linear, action_angular, goal_dist, goal_angle, min_obstacle_dist):
#         # # [-3.14, 0]
#         # r_yaw = -3 * abs(goal_angle)

#         # # [-4, 0]
#         # if abs(goal_angle) < 1:
#         #     r_vangular = -3 * (action_angular**2)
#         # else:
#         #     r_vangular = 0

#         # [-1, 1]
#         r_distance = 2 * (math.exp(-goal_dist) - 1)

#         if goal_dist < 1.5:
#             r_goal = 2/(abs(goal_angle)+1)
#         else:
#             r_goal = 0

#         # [-20, 0]
#         if min_obstacle_dist < 0.6:
#              r_obstacle = -20 + abs(action_angular*3.14)
#         elif min_obstacle_dist < 1.2:
#             r_obstacle = 3 * (abs(action_angular) - 2*abs(action_linear*2-1))
#         else:
#             r_obstacle = 3 * (action_linear - 2*abs(action_angular))

#         # [-2 * (2.2^2), 0]
#         if abs(goal_angle)<0.2:
#             r_vlinear = -0.25 * (1/abs(action_linear+0.1))
#         else:
#             r_vlinear = -(abs(action_linear*2-1)) + abs(action_angular)

#         if min_obstacle_dist > 1.0:
#             r_vang = -1 * abs(goal_angle - (action_angular*3.14))
#         else:
#             r_vang = abs(action_angular)
         
#         reward = r_distance + r_obstacle + r_vlinear + r_vang + r_goal - 1

#         if succeed == SUCCESS:
#             reward += 60000
#         elif succeed == COLLISION_OBSTACLE or succeed == COLLISION_WALL:
#             reward -= 60000
#         return float(reward)


# version29
def get_reward_A(succeed, action_linear, action_angular, goal_dist, goal_angle, min_obstacle_dist):

        r_distance = -(abs(goal_dist*goal_angle)/10)
        # [-20, 0]
        if min_obstacle_dist < 0.6:
             r_obstacle = -10 + abs(action_angular*3.14)
        elif min_obstacle_dist < 1.2:
            r_obstacle = -2 + 2 * (abs(action_angular) - 2*abs(action_linear*2-1))
        else:
            r_obstacle = -2 + 2 * (action_linear - abs(goal_angle - (action_angular*3.14)))

        # [-2 * (2.2^2), 0]
        if abs(goal_angle)<0.2:
            r_vlinear = -0.25 * (1/abs(action_linear+0.5))
        elif abs(goal_angle)>2.5:
            r_vlinear = -2 + 2 * (abs(action_angular) - 2*action_linear)
        else:
            r_vlinear = -2 + abs(action_angular) - (abs(action_linear*2-1))
         
        reward = r_distance + r_obstacle + r_vlinear - 1

        if succeed == SUCCESS:
            reward += 20000
        elif succeed == TIMEOUT:
            reward += 10000
        elif succeed == TUMBLE:
            reward -= 10000
        elif succeed == COLLISION_OBSTACLE or succeed == COLLISION_WALL:
            reward -= 40000
        return float(reward)

# version28
# def get_reward_A(succeed, action_linear, action_angular, goal_dist, goal_angle, min_obstacle_dist):

#         # [-1, 1]
#         r_distance = 1/(goal_dist+0.1) + min_obstacle_dist/2

#         # [-20, 0]
#         if min_obstacle_dist < 0.7:
#              r_obstacle =  -2 * (3.14 - abs(action_angular*3.14)) - abs(action_linear-0.25)
#         elif min_obstacle_dist < 1.2:
#             r_obstacle = 2 * (action_linear - abs(action_angular))
#         else:
#             r_obstacle = 2 * (action_linear - abs(goal_angle - (action_angular*3.14)))

#         # [-2 * (2.2^2), 0]
#         if abs(goal_angle)<0.2:
#             if min_obstacle_dist<0.8:
#                 r_vlinear = - (3.14/abs(action_angular*3.14)) - (1/min_obstacle_dist+0.1)
#             else:
#                 r_vlinear = -0.25 * (1/abs(action_linear+0.3))
#         elif abs(goal_angle)>2.5:
#             r_vlinear = -1 * (2*action_linear - abs(action_angular))
#         else:
#             # r_vlinear = 2 * (abs(action_linear*2-1) - abs(action_angular))
#             r_vlinear = -1 + action_linear + min_obstacle_dist

         
#         reward = r_distance + r_obstacle + r_vlinear - 1

#         if succeed == SUCCESS:
#             reward += 5000
#         elif succeed == TIMEOUT:
#             reward += 10000
#         elif succeed == TUMBLE:
#             reward -= 10000
#         elif succeed == COLLISION_OBSTACLE or succeed == COLLISION_WALL:
#             reward -= 15000
#         return float(reward)


# version36
# def get_reward_A(succeed, action_linear, action_angular, goal_dist, goal_angle, min_obstacle_dist):
#         # [-3.14, 0]
#         r_distance = (2.0/goal_dist) + action_linear

#         # [-4, 0]
#         if min_obstacle_dist < 0.6:
#              r_obstacle = -5 + abs(action_angular) - 2*abs(action_linear-0.25)
#              r_distance = -(2.0/min_obstacle_dist) + 2*(1.0/goal_dist) + abs(goal_angle)
#         else:
#             r_obstacle = -2*abs(goal_angle - (action_angular*3.14)) 

#         if goal_dist < 1.0 and goal_angle < 0.2:
#              r_goal = action_linear - abs(action_angular)
#         elif goal_dist < 1.0 and goal_angle > 0.2:
#              r_goal = abs(action_angular) - action_linear
#         else:
#              r_goal = -3*(1-action_linear)

#         # if abs(goal_angle)>2 and action_linear > 0.5:
#         #      r_away = -2
#         #      if abs(action_angular) < 0.5:
#         #           r_away -= 2
#         # else:
#         #      r_away = 0

#         # if abs(goal_angle)<1 and action_linear < 0.5:
#         #      r_away -= 2


#         reward = r_distance + r_obstacle + r_goal - 1

#         if succeed == SUCCESS:
#             reward += 10000
#         elif succeed == TUMBLE:
#             reward -= 5000
#         elif succeed == COLLISION_OBSTACLE or succeed == COLLISION_WALL:
#             reward -= 10000
#         return float(reward)

# Define your own reward function by defining a new function: 'get_reward_X'
# Replace X with your reward function name and configure it in settings.py

def get_reward_X(succeed, action_linear, action_angular, goal_dist, goal_angle, min_obstacle_dist):
        # [-3.14, 0]
        r_yaw = -1 * abs(goal_angle)

        # [-4, 0]
        r_vangular = -1.2 * abs(action_angular)

        # [-1, 1]
        r_distance = np.sign(goal_dist_initial - goal_dist) * ((goal_dist - goal_dist_initial)**2)

        # [-20, 0]
        if min_obstacle_dist < 0.3:
            r_obstacle = -20
        else:
            r_obstacle = 0

        # [-2 * (2.2^2), 0]
        r_vlinear = -10 * ((0.25 - abs(action_linear))**2)

        reward = r_yaw + r_distance + r_obstacle + r_vlinear + r_vangular - 1

        if succeed == SUCCESS:
            reward += 4000
        elif succeed == COLLISION_OBSTACLE or succeed == COLLISION_WALL:
            reward -= 2000
        return float(reward)

def reward_initalize(init_distance_to_goal):
    global goal_dist_initial
    goal_dist_initial = init_distance_to_goal

function_name = "get_reward_" + REWARD_FUNCTION
reward_function_internal = globals()[function_name]
if reward_function_internal == None:
    quit(f"Error: reward function {function_name} does not exist")
