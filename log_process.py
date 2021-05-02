from datetime import datetime, timedelta, time
import os
import matplotlib.pyplot as plt
import pathlib
from matplotlib import dates as mpl_dates
import argparse


CODE_SERVER_LOG_PATH = os.path.expanduser("~") + "/.local/share/code-server/logs"
LOG_TIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
plt.style.use('seaborn')


def get_exthost_log_paths():
    """
    Returns a list containing absolute file path of each exthost.log.
    """
    log_dir_names = os.listdir(CODE_SERVER_LOG_PATH)
    abs_log_dir_paths = [os.path.join(CODE_SERVER_LOG_PATH, log_dir_name, "extension-host/exthost.log") for log_dir_name in log_dir_names]
    return abs_log_dir_paths


def get_datetime_from_log_line(log_line):
    """
    Expects a log line like so:
    [2021-04-25 18:02:52.310] [exthost] [info] ExtensionService#loadCommonJSModule

    Returns a datetime object for each log line. If not a line with time, returns None.
    """
    if log_line.startswith("["):
        log_datetime = log_line.split("]")[0].lstrip("[")
        log_date_object = datetime.strptime(log_datetime, LOG_TIME_FORMAT)
        return log_date_object


def get_log_activity_interval(log_path, interval={"minutes": 30}):
    """
    Expects a string, log_path, where code-server log exists.

    Code-server log has to be in this format:
    [2021-05-01 21:10:30.781] ___________________________________

    Returns the log times as a dictionary with time interval and the count of logs written in each time interval.
    e.g {"2021-05-01 21:10:30": 1,
         "2021-05-01 21:11:00": 2,
         "2021-05-01 21:11:30": 3}


    Optional argument interval expects a dictionary of the time unit as str to interval value as int.
    e.g {"hours": 1, "seconds": 5} means group data by intervals of 1 hour and 5 seconds. (Pretty silly as well)
    Options available are weeks, days, hours, minutes, seconds, microseconds and miliseconds. 
    However, sorting by anything more than day is useless, due to how the logs are written daily.
    Also sorting by miliseconds and microseconds are also pretty silly.
    """
    delta = timedelta(**interval)  # more dictionary hacks, since timedelta is read-only due to C implementation at lower level
    time_interval_to_log_count = {}

    with open(log_path) as log_file:  # initialize dictionary
        log_date_object = None
        while log_date_object is None:  # readline until not None
            log_date_object = get_datetime_from_log_line(log_file.readline())  # get date
        log_date_object = datetime.combine(log_date_object, time())  # set time to zero for just date
        time_interval_to_log_count = {log_date_object + log_time_object * delta: 0 for log_time_object in range(timedelta(days=1) // delta)}

    with open(log_path) as log_file:
        for log_line in log_file:
            log_date_object = get_datetime_from_log_line(log_line)
            if log_date_object is not None:
                rounded_log_date_object = log_date_object + (datetime.min - log_date_object) % delta  # By adding the remainder, you get a perfectly rounded time
                existing_value = time_interval_to_log_count.get(rounded_log_date_object)
                if existing_value is None:
                    time_interval_to_log_count[rounded_log_date_object] = 1
                else:
                    time_interval_to_log_count[rounded_log_date_object] += 1
    return time_interval_to_log_count


def draw_bar_plot_from_time_dict(interval_to_log_activity, view=True, skip=2, axes_rect=[0.15, 0.3, 0.75, 0.6], save_file=None, dpi=200):
    """
    Expects a dictionary of time intervals to log activity. 
    Draws a bar plot. Optionally save_file is a string specifying the name of the file to be saved as at current directory.

    If view is False, does not show the drawn graph. Defaults to True.
    If save_file is not specified, figure is not stored on disk. Defaults to None.

    axes_rect takes a list of 4 floats, representing x offset, y offset, x scaling and y scaling of the graph respectively. Defaults to a working setting.
    skip skips some of the time x labels on the x axis, so that it does not over staturate the x axis with times, use it to make graph look better.
    """
    fig = plt.figure()
    times = [timing.time().isoformat() for timing in interval_to_log_activity.keys()]
    activity = interval_to_log_activity.values()
    ax = fig.add_axes(axes_rect)
    ax.set_xlabel("Time of log written")
    ax.set_ylabel("Log activity count")
    ax.bar(times, activity)
    ax.set_xticklabels(times, rotation = 75)  # rotates the time by 75 degrees anti clockwise for readability
    for label in ax.xaxis.get_ticklabels()[::skip]:
        label.set_visible(False)

    if view is True:
        fig.show()
    
    if save_file is not None:
        fig.savefig(save_file + "-bar", dpi=dpi)


def draw_line_plot_from_time_dict(interval_to_log_activity, view=True, save_file=None, dpi=200):
    """
    Expects a dictionary of time intervals to log activity. 
    Draws a line plot. Optionally save_file is a string specifying the name of the file to be saved as at current directory.

    If view is False, does not show the drawn graph. Defaults to True.
    If save_file is not specified, figure is not stored on disk. Defaults to None.
    """
    times = list(interval_to_log_activity.keys())
    activity = interval_to_log_activity.values()
    plt.plot(times, activity)
    plt.gcf().autofmt_xdate()
    date_format = mpl_dates.DateFormatter("%m/%d %H:%M:%S")
    plt.gca().xaxis.set_major_formatter(date_format)
    plt.title("Code-server activity to time")
    plt.xlabel("Time of log written")
    plt.ylabel("Log activity count")

    if view is True:
        plt.show()
    
    if save_file is not None:
        plt.savefig(save_file + "-line", dpi=dpi)
    
    plt.close()


def main():
    log_paths = get_exthost_log_paths()
    for log_path in log_paths:
        identifying_folder = pathlib.Path(log_path).parent.parent.name  # the grandparent of exthost.log is unique per day
        print(identifying_folder.center(50, "="))
        interval_to_log_activity = get_log_activity_interval(log_path)
        for key, value in interval_to_log_activity.items():
            print(key, ":", value)
        draw_line_plot_from_time_dict(interval_to_log_activity, view=False, save_file=identifying_folder)
    

if __name__ == "__main__":
    main()