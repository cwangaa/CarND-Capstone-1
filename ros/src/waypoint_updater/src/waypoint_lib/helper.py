import math
import numpy as np
import tf
from tf import transformations as t


def get_traffic_light_color(state):
    # UNKNOWN = 4,
    # GREEN = 2,
    # YELLOW = 1,
    # RED = 0,

    if state == 0:
        return "RED"
    elif state == 1:
        return "YELLOW"
    elif state == 2:
        return "GREEN"
    elif state == 3:
        return "UNKNOWN"


def euclid_dist(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)


def is_velocity_almost_zero(velocity):
    if abs(velocity) < 0.001:
        return True

    return False


def deceleration_rate(velocity, distance):
    if distance < 0.005:
        return 1.0
    return velocity / distance


def create_numpy_repr(waypoints):
    """Create a numpy representation of the waypoints message. Useful for creating kdtrees out of it."""
    points = []
    for waypoint in waypoints:
        x, y, z = waypoint.pose.pose.position.x, waypoint.pose.pose.position.y, waypoint.pose.pose.position.z
        points.append([x, y, z])

    return np.array(points)


def yaw_from_orientation(o):
    # https://answers.ros.org/question/69754/quaternion-transformations-in-python/
    q = (o.x, o.y, o.z, o.w)
    return tf.transformations.euler_from_quaternion(q)[2]


def dist_pose_waypoint(pose, waypoint):
    """Given a pose & a waypoint find the distance between them."""
    dist = euclid_dist(pose.pose.position, waypoint.pose.pose.position)
    return dist


def next_waypoint_index_brute_force(pose, waypoints):
    """Given a current pose find the closest index of from the list of waypoints.

    :arg:
        pose: Current pose (position) of the vehicle.
        waypoints: The list of waypoints from which to find the closest index
    :returns
        The closest index of the waypoint
    """
    dists = [dist_pose_waypoint(pose, waypoint) for waypoint in waypoints]
    closest_wp_idx = dists.index(min(dists))
    wp = waypoints[closest_wp_idx]

    pose_orientation = pose.pose.orientation

    pose_yaw = yaw_from_orientation(pose_orientation)
    angle = math.atan2(wp.pose.pose.position.y - pose.pose.position.y, wp.pose.pose.position.x - pose.pose.position.x)
    delta = abs(pose_yaw - angle)

    while delta > math.pi:
        delta -= math.pi

    total_waypoints = len(waypoints)

    if delta > math.pi/4:
        closest_wp_idx = (closest_wp_idx + 1) % total_waypoints

    return closest_wp_idx


def next_waypoint_index_kdtree(pose, kdtree):
    """Given a current pose find the closest index of from the list of waypoints.

    :arg:
        pose: Current pose (position) of the vehicle.
        kdtree: Precomputed kdtree for doing the nearest neighbor search.
    :returns
        The closest index of the waypoint
    """
    distance, closest_wp_idx = kdtree.query([pose.position.x, pose.position.y, pose.position.z], k=1)
    waypoint = kdtree.data[closest_wp_idx]

    pose_orientation = pose.orientation

    pose_yaw = yaw_from_orientation(pose_orientation)
    angle = math.atan2(waypoint[1] - pose.position.y, waypoint[0] - pose.position.x)
    delta = abs(pose_yaw - angle)

    while delta > math.pi:
        delta -= math.pi

    total_waypoints = len(kdtree.data)

    if delta > math.pi/4:
        closest_wp_idx = (closest_wp_idx + 1) % total_waypoints

    return closest_wp_idx


def tranform_to_pose_coord_xy(pose, x_coords, y_coords):
    x_coords_pose = []
    y_coords_pose = []
    pose_x = pose.pose.position.x
    pose_y = pose.pose.position.y
    pose_yaw = yaw_from_orientation(pose.pose.orientation)
    for x, y in zip(x_coords, y_coords):
        # Translation
        rx = x - pose_x
        ry = y - pose_y
        # Rotation
        rxf = rx * math.cos(pose_yaw) + ry * math.sin(pose_yaw)
        ryf = rx * (-1.0*math.sin(pose_yaw)) + ry * math.cos(pose_yaw)
        x_coords_pose.append(rxf)
        y_coords_pose.append(ryf)

    return x_coords_pose, y_coords_pose


def calc_steer_cte(pose, waypoints, fit_length=10):
    if not fit_length:
        fit_length = len(waypoints)

    if fit_length > len(waypoints):
        return 0.0

    # Get X,Y coords
    x_coords = []
    y_coords = []
    for i in range(fit_length):
        x_coords.append(waypoints[i].pose.pose.position.x)
        y_coords.append(waypoints[i].pose.pose.position.y)

    # Transform to car coordinates
    x_coords_car, y_coords_car = tranform_to_pose_coord_xy(pose, x_coords, y_coords)

    coeffs = np.polyfit(x_coords_car, y_coords_car, 3)
    dist = np.polyval(coeffs, 0.0)

    return dist
