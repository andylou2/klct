# -*- coding: utf-8 -*-
import curses
import locale
import os.path
import time
import sys
import yaml
import logging
from collections import OrderedDict
import klct.ldap.refactored_ldap_service as conn_service
from klct.log import logger
if sys.version_info >= (3, 0):
    import importlib
    importlib.reload(sys)
else:
    reload(sys)
    sys.setdefaultencoding('utf8')
menu_options = ["1. Enter/Validate LDAP Server IP",
                "2. Check Connection to LDAP Server",
                "3. Get Server Information",
                "4. Check LDAP Suffix",
                "5. Input User ID Attribute/User Name Attribute",
                "6. Show List of User-Related ObjectClasses",
                "7. Show List of Users",
                "8. Get a Specific User",
                "9. Input Group ID Attribute/Group Name Attribute",
                "10. Show List of Group Related ObjectClasses",
                "11. Show List of Groups",
                "12. Get Specific Group",
                "13. Add Additional Configuration Options",
                "14. Save/Create Configuration File"]


def klct_curses_setup(stdscr):
    stdscr.keypad(True)
    stdscr.scrollok(True)
    curses.noecho()
    if curses.has_colors():  # enable coloring
        curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(2, curses.COLOR_MAGENTA, curses.COLOR_WHITE)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_WHITE)
    curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_WHITE)
    curses.init_pair(6, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(7, curses.COLOR_GREEN, curses.COLOR_WHITE)
    curses.init_pair(8, curses.COLOR_BLUE, curses.COLOR_WHITE)
    stdscr.bkgd(curses.color_pair(1))
    return stdscr.getmaxyx()


def resize_windows():
    LOG.info("Resizing window")
    var_dict["status_window"].clear()
    var_dict["status_window_text"].clear()
    LOG.info("Status window cleared.")
    screen_dimensions = stdscr.getmaxyx()
    LOG.info("Getting new dimensions: " + str(screen_dimensions))
    var_dict["main_window"] = stdscr.subwin(
        screen_dimensions[0] - 2, screen_dimensions[1] -
        int(screen_dimensions[1] / 3) - 1, 1, 1)
    var_dict["main_window"].keypad(True)
    LOG.info("New main window created with dimensions: " +
             str(screen_dimensions[0] - 2)+"x" +
             str(screen_dimensions[1] - int(screen_dimensions[1] / 3) - 1) +
             " at coordinates: "+str(1)+", "+str(1))
    var_dict["status_window"] = stdscr.subwin(
        screen_dimensions[0] - 2,
        int(screen_dimensions[1] / 3) - 2, 1,
        screen_dimensions[1] - int(screen_dimensions[1] / 3))
    LOG.info("New status window created with dimensions: "+str(
        screen_dimensions[0] - 2)+"x"+str(int(screen_dimensions[1] / 3) - 2) +
             " at coordinates: "+str(1)+", "+str(screen_dimensions[1] -
                                                 int(screen_dimensions[1] /
                                                     3)))
    var_dict["status_window_text"] = stdscr.subwin(
        screen_dimensions[0] - 4, int(screen_dimensions[1] / 3) - 4, 2,
        screen_dimensions[1] - int(screen_dimensions[1] / 3) + 1)
    LOG.info("New status window text created with dimensions: "+str(
        screen_dimensions[0] - 4)+"x"+str(int(screen_dimensions[1] / 3) - 4) +
             " at coordinates: "+str(2)+", "+str(screen_dimensions[1] -
                                                 int(screen_dimensions[1] /
                                                     3) + 1))

    show_console_in_status_window()
    stdscr.refresh()
    LOG.info("Standard Screen Refreshed")
    var_dict["main_window"].refresh()
    LOG.info("Main window Refreshed")
    status_window.refresh()
    LOG.info("Status window Refreshed")
    status_window_text.refresh()
    LOG.info("Status window Text Refreshed")


def limited_addstr(screen, y, x, *args): #args[0] is the string to print
    dims = screen.getmaxyx()
    msg = args[0]
    if len(msg) + x >= dims[1]:
        LOG.warning("String: \"{}\" does not fit on the screen. Truncating.".format(msg))
        msg = msg[:dims[1] - x - 2] + '..'
    if  x < 0 or 1 + y >= dims[0] or y < 0:
        LOG.warning("String: \"{}\" does not fit on the screen. Unable to Truncate.".format(msg))
        return;
    screen.addstr(y, x, msg, *(args[1:]))

def limited_addch(screen, y, x, ch):
    dims = screen.getmaxyx()
    if x < 0:
        x = 0
    if y < 0:
        y = 0
    if y > dims[0]:
        y = dims[0] - 1
    if x > dims[1]:
        x = dims[1] - 1

    screen.addch(y, x, ch)



def display_list_with_numbers(screen, y, x, list_given):
    """Elements in list must be string."""
    num_elements = len(list_given)
    for i in range(num_elements):
        elem_i = str(list_given[i])
        #elem_string = unicode("{i}. {elem}".format(i=i+1, elem=elem_i)) #unicode does not exist in python3.4
        elem_string = "{i}. {elem}".format(i=i+1, elem=elem_i)
        limited_addstr(screen, y + i, x, elem_string)


def display_list_with_numbers_test(screen, y, x, list_given):
    """Elements in list must be string."""
    num_elements = len(list_given)
    for i in range(num_elements):
        elem_i = str(list_given[i])
        elem_i = elem_i.replace('\n', "")
        #elem_string = unicode("{i}. {elem}".format(i=i+1, elem=elem_i)) #unicode does not exist in python3.4
        elem_string = "{i}. {elem}".format(i=i+1, elem=elem_i)
        limited_addstr(screen, y + i, x, elem_string)


def show_instructions(screen):
    """Displays the starting instructions prior to the menu display."""
    curses.curs_set(0)
    screen_dimensions = screen.getmaxyx()
    screen.clear()
    start_instruction = "HOS Keystone-LDAP Configuration Tool."
    limited_addstr(screen, int(screen_dimensions[0]/2),
                  int(screen_dimensions[1]/2) - int(len(start_instruction)/2),
                  start_instruction, curses.A_BOLD | curses.A_COLOR)
    startup_commands = "Press 'm' to go to the menu or 'q' to quit."
    limited_addstr(screen, int(screen_dimensions[0]/2) + 1, int(screen_dimensions[1]/2) - int(len(startup_commands)/2), startup_commands)
    screen.refresh()
    char_press = screen.getch()
    while char_press not in (109, 113):
        if char_press == curses.KEY_RESIZE:
            resize_windows()
            show_instructions(stdscr)
        char_press = screen.getch()
    if char_press == 109:
        screen.clear()
        screen.refresh()
        display_menu()
    elif char_press == 113:
        sys.exit(0)


def my_raw_input(screen, y, x, prompt_string, default=""):
    curses.noecho()
    curses.curs_set(True)
    limited_addstr(screen, y, x, prompt_string, curses.color_pair(2))
    limited_addch(screen, y + 1, x, ">")
    screen.refresh()
    x_coord = x + 1
    str_input_pos = 0
    str_input = []
    c = screen.getch()
    while c != 10:  # 10 == '\n' newline character
        if c == curses.KEY_RESIZE:
            var_dict["status_window"].clear()
            var_dict["status_window_text"].clear()
            screen_dimensions = stdscr.getmaxyx()
            var_dict["main_window"] = stdscr.subwin(
                screen_dimensions[0] - 2, screen_dimensions[1] -
                int(screen_dimensions[1] / 4) - 1, 1, 1)
            var_dict["main_window"].keypad(True)
            var_dict["status_window"] = stdscr.subwin(
                screen_dimensions[0] - 2,
                int(screen_dimensions[1] / 4) - 2, 1,
                screen_dimensions[1] - int(screen_dimensions[1] / 4))
            var_dict["status_window_text"] = stdscr.subwin(
                screen_dimensions[0] - 4, int(screen_dimensions[1] / 4) - 4, 2,
                screen_dimensions[1] - int(screen_dimensions[1] / 4) + 1)

            show_console_in_status_window()
            stdscr.refresh()
            screen.refresh()
            status_window.refresh()
            status_window_text.refresh()
        elif c < 256:
            str_input.append(chr(c))
            limited_addch(screen, y + 1, x_coord, str(chr(c)))
            x_coord += 1
            str_input_pos += 1
        elif c in (263, 8, 330):
            if x_coord > x + 1:
                x_coord -= 1
                screen.refresh()
            limited_addch(screen, y + 1, x_coord, " ")
            if str_input_pos > 0:
                str_input_pos -= 1
            if len(str_input) > 0:
                str_input.pop()
        # screen.move(y + 1, x_coord)
        c = screen.getch()
    string_input = ''.join(str_input)
    string_input = string_input.strip()
    if string_input == "":
        limited_addstr(screen, y+1, x+1, str(default))
        return default
    curses.curs_set(False)
    curses.noecho()
    return string_input


def my_pw_input(screen, y, x, prompt_string):
    """Prompt for input from user. Given a (y, x) coordinate,
    will show a prompt at (y + 1, x). Will echo characters but as an '*',
    to hide the password's characters from showing on the screen."""
    curses.noecho()  # no echoing
    curses.curs_set(True)
    limited_addstr(screen, y, x, prompt_string, curses.color_pair(2))
    limited_addch(screen, y + 1, x, ">")
    screen.refresh()
    x_coord = x + 1
    str_input_pos = 0
    c = screen.getch()
    str_input = []
    while c != 10:
        if c < 256:
            str_input.append(chr(c))
            limited_addch(screen, y + 1, x_coord, "*")
            x_coord += 1
            str_input_pos += 1
        if c in (263, 8, 330):
            if x_coord > x + 1:
                x_coord -= 1
            limited_addch(screen, y + 1, x_coord, " ")
            if str_input_pos > 0:
                str_input_pos -= 1
            if len(str_input) > 0:
                str_input.pop()
        if c == curses.KEY_RESIZE:
            resize_windows()
        screen.move(y + 1, x_coord)
        c = screen.getch()
    pw_input = ''.join(str_input)
    curses.curs_set(False)
    return pw_input


def prompt_char_input(screen, y, x, prompt_string, list_given):
    """Prompt for a single character input from user until user gives a char in
    list_given.Given a (y, x) coordinate, will show a prompt at (y + 1, x)."""
    curses.echo()  # no echoing
    curses.curs_set(True)
    limited_addstr(screen, y, x, prompt_string, curses.color_pair(2))
    limited_addch(screen, y + 1, x, ">")
    screen.refresh()
    ch_input = screen.getstr(y + 1, x + 1, 1).decode(encoding="utf-8")  # 20 = max chars to in string
    LOG.info("list_given: {}".format(list_given))
    LOG.info("char: {}".format(ch_input))
    while ch_input not in list_given:
        limited_addstr(screen, y, x, "                                     ")
        limited_addstr(screen, y + 1, x, "> ")
        limited_addstr(screen, y, x, prompt_string, curses.color_pair(2))
        screen.refresh()
        ch_input = screen.getstr(y + 1, x + 1, 1).decode(encoding="utf-8")

    curses.noecho()
    curses.curs_set(False)
    return ch_input


def my_numb_input(screen, y, x, prompt_string, limit=None, default=None):
    curses.echo()
    curses.curs_set(True)
    limited_addstr(screen, y, x, prompt_string, curses.color_pair(2))
    limited_addstr(screen, y + 1, x, ">            ")
    screen.refresh()
    numb_input = screen.getstr(y + 1, x + 1, 10).decode(encoding="utf-8")
    numb_input = numb_input.strip()
    if numb_input == "":
        limited_addstr(screen, y+1, x+1, str(default))
        curses.noecho()
        curses.curs_set(False)
        return default
    while not numb_input.isdigit():
        limited_addstr(screen, y, x,
                      "                                                      ")
        limited_addstr(screen, y + 1, x, ">                                 ")
        limited_addstr(screen, y, x, prompt_string, curses.color_pair(2))
        numb_input = screen.getstr(y + 1, x + 1, 10).decode(encoding="utf-8")
    if limit is not None:
        if int(numb_input) > limit:
            curses.noecho()
            curses.curs_set(False)
            return my_numb_input(screen, y, x, prompt_string, limit)
        else:
            curses.noecho()
            curses.curs_set(False)
            return int(numb_input)
    else:
        curses.noecho()
        curses.curs_set(False)
        return int(numb_input)


def setup_menu_call(screen, title=""):
    """Typically called at start of a menu method.
    Clears screen, adds title and returns max y and max x in tuple."""
    LOG.info("Setting up menu for: " + title)
    screen.clear()
    screen_dims = screen.getmaxyx()
    limited_addstr(screen, int(screen_dims[0]/6), int(screen_dims[1]/2) - int(len(
        title)/2), title,
                  curses.color_pair(1) | curses.A_BOLD |
                  curses.A_UNDERLINE | curses.A_COLOR)
    return screen_dims


def end_menu_call(screen, current_step):
    screen_dims = screen.getmaxyx()
    command_menu = {1: m.menu_ping_ldap_ip,
                    2: m.menu_check_ldap_connection_adv,
                    3: m.menu_get_server_info,
                    4: m.menu_check_ldap_suffix,
                    5: m.menu_input_user_attributes,
                    6: m.menu_show_list_user_object_classes,
                    7: m.menu_check_user_tree_dn_show_users,
                    8: m.menu_get_specific_user,
                    9: m.menu_input_group_attributes,
                    10: m.menu_show_list_group_object_classes,
                    11: m.menu_check_group_tree_dn_show_groups,
                    12: m.menu_get_specific_group,
                    13: m.menu_additional_config_options,
                    14: m.menu_create_config
                    }
    limited_addstr(screen, int(screen_dims[0]/6) + 2, int(screen_dims[1] / 2) - 28,
                  "Press 'n' for next step, 'r' to retry, or 'm' for menu.",
                  curses.A_BOLD | curses.color_pair(8) | curses.A_STANDOUT)
    character = screen.getch()
    while character not in (109, 110, 114):
        if character == curses.KEY_RESIZE:
            resize_windows()
        character = screen.getch()
    if character == 109:  # 109 == m
        display_menu()
    elif character == 110:  # 114 == r
        command_menu[current_step + 1]()
    elif character == 114:
        command_menu[current_step]()


def ip_not_exists(screen, screen_dims):
    limited_addstr(screen, int(screen_dims[0] / 2) - 2, int(screen_dims[1] / 2) - 26,
                  "No valid IP found. Please complete the previous step",
                  curses.A_BOLD | curses.color_pair(3))
    limited_addstr(screen, int(screen_dims[0] / 2) - 1, int(screen_dims[1] / 2) - 22,
                  "Press p to input ip address, or 'm' for menu",
                  curses.color_pair(5))
    key_press = screen.getch()
    while key_press not in (109, 112):  # 109 == m, 112 == p
        if key_press == curses.KEY_RESIZE:
            resize_windows()
        key_press = screen.getch()
    if key_press == 109:
        display_menu()
    elif key_press == 112:
        menu_ping_ldap_ip()


def show_console_in_status_window():
    LOG.info("Updating console window.")
    var_dict["status_window"].clear()
    var_dict["status_window_text"].clear()
    var_dict["status_window"].box()
    var_dict["status_window_text"].addstr(0, 0, "Keystone-LDAP Configuration",
                                          curses.A_BOLD | curses.A_UNDERLINE)
    dmp = conn_service.HOSYamlDump()
    if bool(configuration_dict):
        global timestamp_string
        tmpfile = "temp_conf_" + timestamp_string + ".yaml"
        dmp.save_config(configuration_dict, tmpfile)
        configuration_dict_yaml_str = dmp.save_config(configuration_dict, None)
        var_dict["status_window_text"].addstr(1, 0,
                                              configuration_dict_yaml_str)
    var_dict["status_window"].refresh()
    var_dict["status_window_text"].refresh()


def display_menu():
    """Displays the menu. Does most of the work for displaying options."""
    stdscr_screen_dimensions = stdscr.getmaxyx()
    screen = stdscr.subwin(stdscr_screen_dimensions[0] - 2,
                           stdscr_screen_dimensions[1] -
                           int(stdscr_screen_dimensions[1] / 3) - 1,
                           1, 1)
    screen.keypad(True)
    screen_dimensions = screen.getmaxyx()
    screen_half_y = int(screen_dimensions[0]/2)
    screen_half_x = int(screen_dimensions[1]/2)
    screen.nodelay(0)
    screen.clear()
    var_dict["status_window"].box()
    show_console_in_status_window()
    screen.refresh()

    menu_selection = -1
    option_num = 0
    while menu_selection < 0:
        menu_highlighting = [0] * (len(menu_options) + 1)
        menu_highlighting[option_num] = curses.A_STANDOUT
        limited_addstr(screen, screen_half_y - 9, screen_half_x - 11,
                      "LDAP Configuration Menu", curses.A_UNDERLINE |
                      curses.color_pair(1) | curses.A_BOLD)
        limited_addstr(screen, screen_half_y - 6, screen_half_x - 25,
                      menu_options[0].encode("utf-8"),
                      menu_highlighting[0] | menu_color[0])
        limited_addstr(screen, screen_half_y - 5, screen_half_x - 25,
                      menu_options[1].encode("utf-8"),
                      menu_highlighting[1] | menu_color[1])
        limited_addstr(screen, screen_half_y - 4, screen_half_x - 25,
                      menu_options[2].encode("utf-8"),
                      menu_highlighting[2] | menu_color[2])
        limited_addstr(screen, screen_half_y - 3, screen_half_x - 25,
                      menu_options[3].encode("utf-8"),
                      menu_highlighting[3] | menu_color[3])
        limited_addstr(screen, screen_half_y - 2, screen_half_x - 25,
                      menu_options[4].encode("utf-8"),
                      menu_highlighting[4] | menu_color[4])
        limited_addstr(screen, screen_half_y - 1, screen_half_x - 25,
                      menu_options[5].encode("utf-8"),
                      menu_highlighting[5] | menu_color[5])
        limited_addstr(screen, screen_half_y + 0, screen_half_x - 25,
                      menu_options[6].encode("utf-8"),
                      menu_highlighting[6] | menu_color[6])
        limited_addstr(screen, screen_half_y + 1, screen_half_x - 25,
                      menu_options[7].encode("utf-8"),
                      menu_highlighting[7] | menu_color[7])
        limited_addstr(screen, screen_half_y + 2, screen_half_x - 25,
                      menu_options[8].encode("utf-8"),
                      menu_highlighting[8] | menu_color[8])
        limited_addstr(screen, screen_half_y + 3, screen_half_x - 25,
                      menu_options[9].encode("utf-8"),
                      menu_highlighting[9] | menu_color[9])
        limited_addstr(screen, screen_half_y + 4, screen_half_x - 25,
                      menu_options[10].encode("utf-8"),
                      menu_highlighting[10] | menu_color[10])
        limited_addstr(screen, screen_half_y + 5, screen_half_x - 25,
                      menu_options[11].encode("utf-8"),
                      menu_highlighting[11] | menu_color[11])
        limited_addstr(screen, screen_half_y + 6, screen_half_x - 25,
                      menu_options[12].encode("utf-8"),
                      menu_highlighting[12] | menu_color[12])
        limited_addstr(screen, screen_half_y + 7, screen_half_x - 25,
                      menu_options[13].encode("utf-8"),
                      menu_highlighting[13] | menu_color[13])
        limited_addstr(screen, screen_half_y + 8, screen_half_x - 25, "15. Exit",
                      menu_highlighting[14] | curses.color_pair(3))
        screen.refresh()
        key_press = screen.getch()
        if key_press == curses.KEY_RESIZE:
            stdscr.clear()
            screen.clear()
            screen_dimensions = stdscr.getmaxyx()
            screen = stdscr.subwin(screen_dimensions[0] - 2,
                                   screen_dimensions[1] -
                                   int(screen_dimensions[1] / 3) - 1,
                                   1, 1)
            screen.keypad(True)
            main_screen_dimensions = screen.getmaxyx()
            screen_half_y = int(main_screen_dimensions[0]/2)
            screen_half_x = int(main_screen_dimensions[1]/2)
            resize_windows()
            stdscr.refresh()
            screen.refresh()
            status_window.refresh()
            status_window_text.refresh()
        elif key_press == curses.KEY_UP:
            option_num = (option_num - 1) % (len(menu_options) + 1)
        elif key_press == curses.KEY_DOWN:
            option_num = (option_num + 1) % (len(menu_options) + 1)
        elif key_press == ord('\n'):
            menu_selection = option_num
            if option_num == 0:
                m.menu_ping_ldap_ip()
            elif option_num == 1:
                m.menu_check_ldap_connection_adv()
            elif option_num == 2:
                m.menu_get_server_info()
            elif option_num == 3:
                m.menu_check_ldap_suffix()
            elif option_num == 4:
                m.menu_input_user_attributes()
            elif option_num == 5:
                m.menu_show_list_user_object_classes()
            elif option_num == 6:
                m.menu_check_user_tree_dn_show_users()
            elif option_num == 7:
                m.menu_get_specific_user()
            elif option_num == 8:
                m.menu_input_group_attributes()
            elif option_num == 9:
                m.menu_show_list_group_object_classes()
            elif option_num == 10:
                m.menu_check_group_tree_dn_show_groups()
            elif option_num == 11:
                m.menu_get_specific_group()
            elif option_num == 12:
                m.menu_additional_config_options()
            elif option_num == 13:
                m.menu_create_config()
            elif option_num == 14:
                if var_dict["conn"] != "none":
                    var_dict["conn"].unbind()
                sys.exit(0)
            else:
                display_menu()
    curses.curs_set(1)

class Menu_Steps(object):
    def __init__(self):
        self.nv = conn_service.NetworkValidator()
        self.ldap_conn = conn_service.LDAPConnection()
        self.ldap_service = None
        self.hos_yaml = None

    def _adv_ldap_setup_prompts(self, screen, max_yx):
        host_ip = configuration_dict["url"]
        temp_str = my_numb_input(screen, int(max_yx[0] / 6) + 4,
                                 int(max_yx[1] / 2) - 22,
                                 "Please enter the port number. Default is "
                                 "389.", None, 389)

        port_numb = int(temp_str)

        userpw_y_or_n = prompt_char_input(screen, int(max_yx[0] / 6) + 6,
                                          int(max_yx[1] / 2) - 22,
                                          "Does LDAP server require User/Pass? "
                                          "[y/n]", ('y', 'n'))
        cert_prompt_offset = 14
        if userpw_y_or_n == 'y':
            user_name = my_raw_input(screen, int(max_yx[0] / 6) + 8,
                                     int(max_yx[1] / 2) - 22,
                                     "Please input your username.")
            # if want password hidden as "*" change my_raw_input to my_pw_input
            pass_wd = my_raw_input(screen, int(max_yx[0] / 6) + 10,
                                   int(max_yx[1] / 2) - 22,
                                   "Please type your password.")
            tls_y_coord = int(max_yx[0] / 6) + 12
        else:
            cert_prompt_offset -= 4
            user_name = None
            pass_wd = None
            tls_y_coord = int(max_yx[0] / 6) + 8

        tls_y_or_n = prompt_char_input(screen, tls_y_coord,
                                       int(max_yx[1] / 2) -
                                       22,
                                       "Is TLS enabled? Enter [y/n]",
                                       ('y', 'n'))
        if tls_y_or_n == 'n':
            tls_cert_path = None
        else:
            tls_cert_path = my_raw_input(screen,
                                         int(max_yx[
                                                 0] / 6) + cert_prompt_offset,
                                         int(max_yx[1] / 2) - 22,
                                         "Please enter the path "
                                         "of the TLS certificate.")
            while not os.path.isfile(tls_cert_path):
                limited_addstr(screen,
                               int(max_yx[0] / 6) + cert_prompt_offset,
                               int(max_yx[1] / 2) - 22,
                               "                                              ")
                limited_addstr(screen,
                               int(max_yx[0] / 6) + cert_prompt_offset + 1,
                               int(max_yx[1] / 2) - 22,
                               ">                                              ")
                tls_cert_path = my_raw_input(screen,
                                             int(max_yx[0] / 6) +
                                             cert_prompt_offset,
                                             int(max_yx[1] / 2) - 22,
                                             "File not found. Please try again.")
        return [host_ip, port_numb, user_name, pass_wd, tls_y_or_n,
                tls_cert_path]

    def _prompt_base_dn(screen):
        screen_dims = setup_menu_call(screen, "Prompt Base Distinguished Name")
        conn_info = var_dict["conn_info"]
        conn = conn_info['conn']
        prompt_str = "Please enter the base dn. (e.g. dc=openstack,dc=org)"
        base_dn = my_raw_input(screen, int(screen_dims[0] / 6) + 6,
                               int(screen_dims[1] / 2) - int(
                                   len(prompt_str) / 2),
                               prompt_str)
        limited_addstr(screen, int(screen_dims[0] / 2) - 2,
                       int(screen_dims[1] / 2) - 10,
                       "Validating suffix (base DN)...",
                       curses.color_pair(5) | curses.A_BOLD)
        screen.refresh()
        results = conn_service.check_ldap_suffix(conn, base_dn)
        limited_addstr(screen, int(screen_dims[0] / 2) - 2,
                       int(screen_dims[1] / 2) - 10,
                       "                              ")
        if results["exit_status"] == 1:
            configuration_dict["suffix"] = base_dn
            menu_options[3] = u"4. Check LDAP Suffix ✓"
            menu_color[3] = curses.color_pair(7)
            show_console_in_status_window()
            end_message = "{base} is valid and has been added to " \
                          "configuration.".format(
                base=base_dn)
            limited_addstr(screen, int(screen_dims[0] / 2) - 4,
                           int(screen_dims[1] / 2) - int(len(end_message) / 2),
                           end_message,
                           curses.color_pair(6) |
                           curses.A_BOLD)
            limited_addstr(screen, int(screen_dims[0] / 6) + 2,
                           int(screen_dims[1] / 2) -
                           25,
                           "Press 'n' for next step, 'r' to retry, or 'm' for "
                           "menu.",
                           curses.A_BOLD | curses.A_STANDOUT | curses.color_pair(
                               8))
        else:
            message_color = 3
            limited_addstr(screen, int(screen_dims[0] / 6) + 2,
                           int(screen_dims[1] / 2) - int(
                               len(results['message']) / 2),
                           results['message'],
                           curses.color_pair(message_color) | curses.A_BOLD)
            limited_addstr(screen, int(screen_dims[0] / 6) + 2,
                           int(screen_dims[1] / 2) -
                           28,
                           "Press 'n' for next step, 'r' to retry, or 'm' for "
                           "menu.",
                           curses.A_BOLD | curses.A_STANDOUT | curses.color_pair(
                               8))
        c = screen.getch()
        while c not in (109, 110, 114):
            if c == curses.KEY_RESIZE:
                resize_windows()
            c = screen.getch()
        if c == 109:
            display_menu()
        elif c == 110:
            menu_input_user_attributes()
        elif c == 114:
            menu_check_ldap_suffix()

    def _check_user_config_dict(self, screen_dims):
        if var_dict["conn"] == "none":
            no_conn_info_msg = \
                "No LDAP server found. Please complete steps 1 and 2."
            limited_addstr(var_dict["main_window"],
                           int(screen_dims[0] / 2),
                           int(screen_dims[1] / 2) - int(
                               len(no_conn_info_msg) / 2),
                           no_conn_info_msg,
                           curses.color_pair(3) | curses.A_BOLD)
            if "user_tree_dn" not in configuration_dict \
                    or "user_id_attribute" not in configuration_dict \
                    or "user_object_class" not in configuration_dict:
                no_user_info_msg = \
                    "Could not find user attribute information. " \
                    "Please complete step 5."
                limited_addstr(var_dict["main_window"],
                               int(screen_dims[0] / 2) + 2,
                               int(screen_dims[1] / 2) - int(
                                   len(no_user_info_msg) / 2),
                               no_user_info_msg,
                               curses.color_pair(3) | curses.A_BOLD)
            return False
        if "user_tree_dn" not in configuration_dict \
                or "user_id_attribute" not in configuration_dict \
                or "user_object_class" not in configuration_dict:
            no_user_info_msg = \
                "Could not find user attribute information. " \
                "Please complete step 5."
            limited_addstr(var_dict["main_window"],
                           int(screen_dims[0] / 2) + 2,
                           int(screen_dims[1] / 2) - len(
                               no_user_info_msg),
                           no_user_info_msg,
                           curses.color_pair(3) | curses.A_BOLD)
            return False
        return True

    def _check_group_config_dict(self, screen_dims):
        if var_dict["conn"] == "none":
            no_conn_info_msg = \
                "No LDAP server found. Please complete steps 1 and 2."
            limited_addstr(var_dict["main_window"],
                int(screen_dims[0] / 2), int(screen_dims[1] / 2) - int(len(
                    no_conn_info_msg) / 2),
                no_conn_info_msg, curses.color_pair(3) | curses.A_BOLD)
            return False
        if "group_tree_dn" not in configuration_dict or \
                        "group_id_attribute" not in configuration_dict or \
                        "group_name_attribute" not in configuration_dict:
            no_group_info_msg = "Could not find group attribute information" \
                                ". Please complete step 9."
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2) + 2,
                                           int(screen_dims[1] / 2) -
                                           len(no_group_info_msg),
                                           no_group_info_msg,
                                           curses.color_pair(
                                               3) | curses.A_BOLD)
            return False
        return True

    def menu_ping_ldap_ip(self):
        """Displays a screen prompting user for IP address and then
        pings that IP address to see if it able to send a response."""
        LOG.info("Prompting for IP.")
        screen_dims = setup_menu_call(var_dict["main_window"],
                                      "1. Enter/Validate LDAP Server IP")
        prompt_ip_string = "Please Enter the IP Address of the LDAP server."
        ip_string = my_raw_input(var_dict["main_window"],
                                 int(screen_dims[0] / 6) + 4,
                                 int(screen_dims[1] / 2) - int(len(
                                     prompt_ip_string) / 2),
                                 prompt_ip_string)
        limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2) - 7,
                                       int(screen_dims[1] / 2) - 12,
                                       "Attempting to ping IP...",
                                       curses.color_pair(5) | curses.A_BLINK)
        var_dict["main_window"].refresh()

        try:
            results = self.nv.ping_ldap_server(ip_string)
        except conn_service.LDAPNetworkException as e:
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 6) + 7,
                                           int(screen_dims[1] / 2) -
                                           int(len(str(e)) / 2), str(e),
                                           curses.color_pair(3))
            limited_addstr(var_dict["main_window"],
                           int(screen_dims[0] / 2) - 7,
                           int(screen_dims[1] / 2) - 12,
                           "                        ")
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 6) + 2,
                                           int(screen_dims[1] / 2) - 23,
                                           "Press 'r' to retry this step, "
                                           "or 'm' for menu.",
                                           curses.A_BOLD | curses.A_STANDOUT |
                                           curses.color_pair(8))
            temp_char = var_dict["main_window"].getch()
            while temp_char not in (110, 109, 114):
                # 109 = 'm', 110 = 'n', 114 = 'r'
                if temp_char == curses.KEY_RESIZE:
                    resize_windows()
                temp_char = var_dict["main_window"].getch()
            if temp_char == 109:
                display_menu()
            elif temp_char == 110:
                self.menu_check_ldap_connection_adv(1)
            elif temp_char == 114:
                self.menu_ping_ldap_ip()

        limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2) - 7,
                                       int(screen_dims[1] / 2) - 12,
                                       "                        ")
        message = "Successfully pinged {}".format(results)
        limited_addstr(var_dict["main_window"], int(screen_dims[0] / 6) + 7,
                       int(screen_dims[1] / 2) -
                       int(len(str(message)) / 2), str(message),
                       curses.color_pair(6))
        limited_addstr(var_dict["main_window"], int(screen_dims[0] / 6) + 8,
                                  int(screen_dims[1] / 2) - 26,
                                  "This IP will automatically be used in "
                                  "the next steps.",
                                  curses.color_pair(4) | curses.A_BOLD)
        end_msg = "Press 'n' to move on to next step, 'r' to retry, or 'm' " \
             "for menu."
        limited_addstr(var_dict["main_window"], int(screen_dims[0] / 6) + 2,
                                  int(screen_dims[1] / 2) - int(len(
                                      end_msg) / 2),
                                  end_msg, curses.A_BOLD |
                                  curses.color_pair(8) |
                                  curses.A_STANDOUT)
        menu_options[0] = u"1. Ping LDAP Server IP ✓"
        menu_color[0] = curses.color_pair(7)
        configuration_dict["url"] = results
        show_console_in_status_window()

        temp_char = var_dict["main_window"].getch()
        while temp_char not in (110, 109, 114):
            # 109 = 'm', 110 = 'n', 114 = 'r'
            if temp_char == curses.KEY_RESIZE:
                resize_windows()
            temp_char = var_dict["main_window"].getch()
        if temp_char == 109:
            display_menu()
        elif temp_char == 110:
            self.menu_check_ldap_connection_adv(1)
        elif temp_char == 114:
            self.menu_ping_ldap_ip()

    def menu_check_ldap_connection_adv(self, skip=0):
        max_yx = setup_menu_call(var_dict["main_window"],
                                 "2. Check Connection to LDAP Server")
        if "url" not in configuration_dict:
            LOG.debug("No ip found.")
            ip_not_exists(var_dict["main_window"], max_yx)
        else:
            if skip == 0:
                y_n = prompt_char_input(
                    var_dict["main_window"], int(max_yx[0] / 2) - 4,
                                             int(max_yx[1] / 2) - 26,
                    "Valid IP has been found, would you like to use this? [y/n]",
                    ('y', 'n'))
            else:
                y_n = 'y'
            setup_menu_call(var_dict["main_window"],
                            "2. Check Connection to LDAP Server")
            if y_n == 'y':
                LOG.info("Prompting for connection information.")
                adv_ldap_inputs = self._adv_ldap_setup_prompts(
                    var_dict["main_window"],
                    max_yx)
                host_ip = adv_ldap_inputs[0]
                port_numb = adv_ldap_inputs[1]
                user_name = adv_ldap_inputs[2]
                pass_wd = adv_ldap_inputs[3]
                tls_y_or_n = adv_ldap_inputs[4]
                tls_cert_path = adv_ldap_inputs[5]
                attempt_message = "Attempting to connect to LDAP server..."
                limited_addstr(var_dict["main_window"],
                    int(max_yx[0] / 6) + 17, int(max_yx[1] / 2) - int(len(
                        attempt_message) / 2),
                    attempt_message,
                    curses.color_pair(5))
                var_dict["main_window"].refresh()
                try:
                    self.ldap_conn.connect_ldap_server(host_ip, port_numb, user_name, pass_wd, tls_y_or_n, tls_cert_path)
                    self.ldap_service = conn_service.LDAPService(self.ldap_conn.conn, self.ldap_conn.server)
                except conn_service.LDAPConnectionException as e:
                    limited_addstr(var_dict["main_window"],
                                   int(max_yx[0] / 6) + 17,
                                   int(max_yx[1] / 2) - int(
                                       len(attempt_message) / 2),
                                   "                                       ")
                    menu_color[1] = curses.color_pair(3)
                    limited_addstr(var_dict["main_window"], int(max_yx[0] / 6) + 18,
                                   int(max_yx[1] / 2) - int(len(str(e)) / 2), str(e),
                                   curses.color_pair(3) | curses.A_BOLD)

                    limited_addstr(var_dict["main_window"], int(max_yx[0] / 6) + 2,
                                   int(max_yx[1] / 2) - 18,
                                   "Press 'r' to retry, or 'm' for menu.",
                                   curses.color_pair(8) | curses.A_STANDOUT | curses.A_BOLD)
                    char = var_dict["main_window"].getch()
                    while char not in (109, 114):
                        if char == curses.KEY_RESIZE:
                            resize_windows()
                        char = var_dict["main_window"].getch()
                    if char == 109:
                        display_menu()
                    elif char == 114:
                        self.menu_check_ldap_connection_adv(1)

                limited_addstr(var_dict["main_window"],
                               int(max_yx[0] / 6) + 17,
                               int(max_yx[1] / 2) - int(
                                   len(attempt_message) / 2),
                               "                                       ")
                var_dict["conn"] = self.ldap_conn.conn
                var_dict["server"] = self.ldap_conn.server
                if not var_dict["port_added"]:
                    configuration_dict["url"] = configuration_dict[
                                                    "url"] + ":" + \
                                                str(port_numb)
                    var_dict["port_added"] = True
                if user_name is not None:
                    configuration_dict["user"] = user_name
                if pass_wd is not None:
                    configuration_dict["password"] = pass_wd
                show_console_in_status_window()
                if tls_cert_path is not None:
                    configuration_dict["tls_cacertfile"] = tls_cert_path
                    show_console_in_status_window()
                    screen.refresh()
                message = "Successfully connected to {}".format(configuration_dict["url"])
                limited_addstr(var_dict["main_window"], int(max_yx[0] / 6) + 18,
                               int(max_yx[1] / 2) - int(
                                   len(message) / 2), message, curses.color_pair(6) | curses.A_BOLD)
                menu_options[1] = u"2. Check Connection to LDAP ✓"
                menu_color[1] = curses.color_pair(7)
                adv_ldap_end_prompt = "Press 'n' to move on to next step, 'r' to retry, or 'm' for menu."
                limited_addstr(var_dict["main_window"], int(max_yx[0] / 6) + 2,
                               int(max_yx[1] / 2) -
                               int(len(adv_ldap_end_prompt) / 2),
                               adv_ldap_end_prompt,
                               curses.A_BOLD | curses.color_pair(
                                   8) | curses.A_STANDOUT)
                character = var_dict["main_window"].getch()
                while character not in (109, 110, 114):
                    if character == curses.KEY_RESIZE:
                        resize_windows()
                    character = var_dict["main_window"].getch()
                if character == 109:  # 109 == m
                    display_menu()
                elif character == 110:  # 110 == n
                    self.menu_get_server_info()
                elif character == 114:
                    self.menu_check_ldap_connection_adv(1)
            else:
                self.menu_ping_ldap_ip()

    def menu_get_server_info(self):
        """Displays server information on screen.
        Currently only displays version and type,  but later will add
        more information."""
        screen_dims = setup_menu_call(var_dict["main_window"],
                                      "3. Get Server Information")
        if self.ldap_conn.conn == None or self.ldap_conn.server == None:
            error_msg = "No LDAP server found. Press any key to go to the menu."
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2),
                                           int(screen_dims[1] / 2) - int(len(error_msg) / 2),
                                           error_msg, curses.color_pair(3) | curses.A_BOLD)
            var_dict["main_window"].getch()
            display_menu()
        else:
            try:
                server_info_dict = self.ldap_service.retrieve_server_info()
            except conn_service.LDAPQueryException as e:
                menu_color[2] = curses.color_pair(3)
                limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2) + 1, int(screen_dims[1] / 2) - len(str(e))/2, str(e), curses.color_pair(3))
                end_menu_call(var_dict["main_window"], 3)

            menu_options[2] = u"3. Get Server Information ✓"
            menu_color[2] = curses.color_pair(7)
            version = str(server_info_dict["version"])
            ldap_type = str(server_info_dict["type"])
            strlen = len(ldap_type)
            if len(version) > len(ldap_type):
                strlen = len(version)
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 6) + 6,
                                           int(screen_dims[1] / 2) -
                                           int(strlen / 2),
                                           version, curses.color_pair(5))
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 6) + 7,
                                           int(screen_dims[1] / 2) -
                                           int(strlen / 2),
                                           ldap_type, curses.color_pair(5))
            var_dict["main_window"].refresh()

        limited_addstr(var_dict["main_window"], int(screen_dims[0] / 6) + 4,
                                       int(screen_dims[1] / 2) - 10,
                                       "Server Information:",
                                       curses.A_BOLD)
        end_menu_call(var_dict["main_window"], 3)

    def menu_check_ldap_suffix(self):
        """If failure, may be due to invalid credentials.
        May want to alert user of this later on."""
        screen_dims = setup_menu_call(var_dict["main_window"],
                                      "4. Check LDAP Suffix")
        if self.ldap_conn.conn == None or self.ldap_conn.server == None:
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2),
                                           int(screen_dims[1] / 2) - 28,
                                           "No LDAP server found. "
                                           "Press any key to go to the menu.")
            var_dict["main_window"].getch()
            display_menu()
        else:
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2),
                                           int(screen_dims[1] / 2) - 9,
                                           "Fetching base dn...",
                                           curses.color_pair(5))
            try:
                base_dn = self.ldap_service.get_ldap_suffix()
            except conn_service.LDAPQueryException as e:
                limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2), int(screen_dims[1] / 2) - 9, "                   ")
                menu_color[3] = curses.color_pair(3)
                limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2) + 1, int(screen_dims[1] / 2) - len(str(e)) / 2, str(e))
                self._prompt_base_dn(var_dict["main_window"])

            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2),
                           int(screen_dims[1] / 2) - 9,
                           "                   ",
                           curses.color_pair(5))
            menu_options[3] = u"4. Check LDAP Suffix ✓"
            menu_color[3] = curses.color_pair(7)
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 6) + 6,
                                           int(screen_dims[1] / 2) -
                                           (int(len(base_dn) / 2) + 8),
                                           base_dn + " is your base dn.",
                                           curses.A_BOLD)
            y_n = prompt_char_input(var_dict["main_window"],
                                    int(screen_dims[0] / 6) + 7,
                                    int(screen_dims[1] / 2) - 18,
                                    "Is this information correct? [y/n]",
                                    ('y', 'n'))
            if y_n == 'n':
                self._prompt_base_dn(var_dict["main_window"])
            else:
                configuration_dict["suffix"] = base_dn
                show_console_in_status_window()
                end_message = "{} added to configuration file.".format(base_dn)
                limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2) - 4,
                                               int(screen_dims[1] / 2) -
                                               int(len(end_message) / 2),
                                               end_message,
                                               curses.color_pair(6) |
                                               curses.A_BOLD)

            end_menu_call(var_dict["main_window"], 4)

    def menu_input_user_attributes(self):
        screen_dims = setup_menu_call(
            var_dict["main_window"],
            "5. Input User ID Attribute/User Name Attribute")
        if self.ldap_conn.conn == None or self.ldap_conn.server == None:
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2),
                                           int(screen_dims[1] / 2) - 23,
                                           "No LDAP server found. "
                                           "Press any key to go to the menu.")
            var_dict["main_window"].getch()
            display_menu()
        else:
            LOG.info("Prompting for user information.")
            user_id_attr_prompt = "What is the user id attribute?"
            user_name_attr_prompt = "What is the user name attribute?"
            user_tree_dn_prompt = "What is the user tree DN, " \
                                  "not including the base DN (e.g. ou=Users)?"
            if "suffix" in configuration_dict:
                user_tree_dn = my_raw_input(var_dict["main_window"],
                                            int(screen_dims[0] / 6) + 4,
                                            int(screen_dims[1] / 2) -
                                            int(len(user_tree_dn_prompt) / 2),
                                            user_tree_dn_prompt)
                user_id_attribute = my_raw_input(
                    var_dict["main_window"],
                    int(screen_dims[0] / 6) + 6,
                    int(screen_dims[1] / 2) - int(
                        len(user_tree_dn_prompt) / 2),
                    user_id_attr_prompt)
                user_name_attribute = my_raw_input(
                    var_dict["main_window"],
                    int(screen_dims[0] / 6) + 8,
                    int(screen_dims[1] / 2) - int(
                        len(user_tree_dn_prompt) / 2),
                    user_name_attr_prompt)
            else:
                limited_addstr(var_dict["main_window"],
                    int(screen_dims[0] / 2), int(screen_dims[1] / 2) - 29,
                    "No Suffix (base DN) found. Press any key to go to the menu.")
                var_dict["main_window"].getch()
                return display_menu()
            attempt_message = "Verifying information... Please wait."
            blank_message = "                                     "
            limited_addstr(var_dict["main_window"],
                int(screen_dims[0] / 6) + 17,
                int(screen_dims[1] / 2) - int(len(attempt_message) / 2),
                attempt_message,
                curses.color_pair(5))
            var_dict["main_window"].refresh()
            try:
                results = self.ldap_service.validate_info(user_tree_dn + "," + configuration_dict["suffix"], user_id_attribute, user_name_attribute)
            except conn_service.LDAPQueryException as e:
                limited_addstr(var_dict["main_window"], int(screen_dims[0] / 6) + 17, int(screen_dims[1] / 2) - int(len(attempt_message) / 2), blank_message)
                limited_addstr(var_dict["main_window"], int(screen_dims[0] / 6) + 12, int(screen_dims[1] / 2) - int(len(str(e)) / 2), str(e), curses.color_pair(3) | curses.A_BOLD)
                menu_color[4] = curses.color_pair(3)
                end_menu_call(var_dict["main_window"], 5)

            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 6) + 17, int(screen_dims[1] / 2) - int(len(attempt_message) / 2), blank_message)
            var_dict["main_window"].refresh()

            configuration_dict["user_tree_dn"] = user_tree_dn + "," + configuration_dict["suffix"]
            configuration_dict["user_id_attribute"] = user_id_attribute
            configuration_dict["user_name_attribute"] = user_name_attribute
            show_console_in_status_window()
            menu_options[4] = u"5. Input User ID Attribute/" \
                              u"User Name Attribute ✓"
            menu_color[4] = curses.color_pair(7)
            limited_addstr(var_dict["main_window"],
                int(screen_dims[0] / 6) + 11,
                int(screen_dims[1] / 2) - int(len(results) / 2),
                results, curses.color_pair(6) | curses.A_BOLD)
            update_message = "Configuration has been updated with this information."
            limited_addstr(var_dict["main_window"],
                int(screen_dims[0] / 6) + 12,
                int(screen_dims[1] / 2) - int(len(update_message) / 2),
                update_message, curses.color_pair(6) | curses.A_BOLD)

            end_menu_call(var_dict["main_window"], 5)

    def menu_show_list_user_object_classes(self):
        screen_dims = setup_menu_call(
            var_dict["main_window"],
            "6. Show List of User-Related ObjectClasses")
        var_dict["main_window"].refresh()
        if self.ldap_conn.conn == None or self.ldap_conn.server == None or "suffix" not in configuration_dict:
            prompt_string = "No connection to server found or no " \
                            "suffix (base DN). Press any key to go to the menu."
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2),
                                           int(screen_dims[1] / 2) -
                                           int(len(prompt_string) / 2),
                                           prompt_string,
                                           curses.color_pair(
                                               3) | curses.A_BOLD)
            var_dict["main_window"].getch()
            display_menu()
        else:
            retrieving_string = "Retrieving list of object classes..."
            blnk_retrieve_str = "                                    "
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2) - 2,
                                           int(screen_dims[1] / 2) -
                                           int(len(retrieving_string) / 2),
                                           retrieving_string,
                                           curses.color_pair(5))
            var_dict["main_window"].refresh()

            # base_dn = configuration_dict["suffix"]
            if "user_id_attribute" in configuration_dict and "user_tree_dn" in \
                    configuration_dict:
                user_id_attribute = configuration_dict["user_id_attribute"]
                user_dn = configuration_dict["user_tree_dn"]
                try:
                    return_values = self.ldap_service.list_object_classes(user_dn, user_id_attribute)
                except conn_service.LDAPQueryException as e:
                    limited_addstr(var_dict["main_window"],
                                   int(screen_dims[0] / 2) - 2,
                                   int(screen_dims[1] / 2) - int(
                                       len(blnk_retrieve_str) / 2),
                                   blnk_retrieve_str)
                    menu_color[5] = curses.color_pair(3)
                    limited_addstr(var_dict["main_window"],
                                   int(screen_dims[0] / 2) - 3,
                                   int(screen_dims[1] / 2) - 12,
                                   "No object classes found.")
                    end_menu_call(var_dict["main_window"], 6)

                limited_addstr(var_dict["main_window"],
                    int(screen_dims[0] / 2) - 2,
                    int(screen_dims[1] / 2) - int(len(blnk_retrieve_str) / 2),
                    blnk_retrieve_str)

                LOG.info("Displaying user object classes.")
                menu_options[5] = u"6. Show List of User-Related ObjectClasses ✓"
                menu_color[5] = curses.color_pair(7)
                limited_addstr(var_dict["main_window"], int(screen_dims[0] / 6) + 4,
                                               int(screen_dims[
                                                       1] / 2) - 15,
                                               "User Object classes:")
                object_classes_list = return_values + ["None of the above"]
                display_list_with_numbers(
                    var_dict["main_window"],
                    int(screen_dims[0] / 6) + 5,
                    int(screen_dims[1] / 2) - 15,
                    object_classes_list)
                num_obj_classes = len(object_classes_list)
                choice = my_numb_input(
                    var_dict["main_window"],
                    int(screen_dims[0] / 6) + num_obj_classes + 5,
                    int(screen_dims[1] / 2) - 15,
                    "Please choose a number.", num_obj_classes)
                if choice == num_obj_classes:
                    usr_obj_class = my_raw_input(
                        var_dict["main_window"],
                        int(screen_dims[0] / 6) + num_obj_classes + 7,
                        int(screen_dims[1] / 2) - 15,
                        "Please enter the user object class")
                    try:
                        ret = self.ldap_service.validate_object_class(user_dn,
                                                             usr_obj_class)
                    except conn_service.LDAPQueryException as e:
                        limited_addstr(var_dict["main_window"],
                                       int(screen_dims[0] / 2) - 3,
                                       int(screen_dims[1] / 2) - int(len(str(e))/2),
                                       str(e),
                                       curses.color_pair(3) | curses.A_BOLD)
                        end_menu_call(var_dict["main_window"], 6)

                    configuration_dict["user_object_class"] = usr_obj_class
                    limited_addstr(var_dict["main_window"],
                                   int(screen_dims[0] / 2) - 3,
                                   int(screen_dims[1] / 2) - len(ret) / 2, ret,
                                   curses.color_pair(6) | curses.A_BOLD)
                else:
                    usr_obj_class = str(object_classes_list[choice - 1])
                    configuration_dict["user_object_class"] = usr_obj_class
                show_console_in_status_window()
                end_message = "{} has been added to configuration.".format(usr_obj_class)
                var_dict["main_window"].addstr(int(screen_dims[0] / 2) - 4,
                                           int(screen_dims[1] / 2) -
                                           int(len(end_message) / 2),
                                           end_message,
                                           curses.color_pair(6) |
                                           curses.A_BOLD)
                show_console_in_status_window()
                end_menu_call(var_dict["main_window"], 6)
            else:
                limited_addstr(var_dict["main_window"],
                    int(screen_dims[0] / 2) - 2,
                    int(screen_dims[1] / 2) - int(len(blnk_retrieve_str) / 2),
                    blnk_retrieve_str)
                error_prompt = "Please input the user id attribute in step 5."
                limited_addstr(var_dict["main_window"],
                    int(screen_dims[0] / 2) - 4,
                    int(screen_dims[1] / 2) - int(len(error_prompt) / 2),
                    error_prompt,
                    curses.color_pair(3) | curses.A_BOLD)
                limited_addstr(var_dict["main_window"],
                    int(screen_dims[0] / 6) + 2,
                    int(screen_dims[1] / 2) - 14,
                    "Press 'm' to go to the menu.",
                    curses.A_BOLD | curses.A_STANDOUT | curses.color_pair(8))
                c = var_dict["main_window"].getch()
                while c != 109:
                    c = var_dict["main_window"].getch()
                if c == 109:
                    display_menu()

    def menu_check_user_tree_dn_show_users(self):
        screen_dims = setup_menu_call(
            var_dict["main_window"],
            "7. Show List of Users")
        if self._check_user_config_dict(screen_dims):
            conn = var_dict["conn"]
            user_tree_dn = configuration_dict["user_tree_dn"]
            user_id_attribute = configuration_dict["user_id_attribute"]
            user_name_attribute = configuration_dict["user_name_attribute"]
            object_class = configuration_dict["user_object_class"]
            maximum = screen_dims[0] - int(screen_dims[0] / 6) - 7
            limit_prompt = "How many users would you like to see? Maximum: {}".format(maximum)
            limit = my_numb_input(var_dict["main_window"],
                                  int(screen_dims[0] / 6) + 4,
                                  int(screen_dims[1] / 8), limit_prompt)
            limit = min(maximum, limit)
            try:
                entries = self.ldap_service.list_entries(user_tree_dn,
                                                      user_id_attribute,
                                                      user_name_attribute,
                                                      object_class, limit)
            except conn_service.LDAPQueryException as e:
                menu_color[6] = curses.color_pair(3)
                limited_addstr(var_dict["main_window"],
                               int(screen_dims[0] / 2) - 2,
                               int(screen_dims[1] / 2) - int(len(str(e)) / 2), str(e),
                               curses.color_pair(3) | curses.A_BOLD)
                end_menu_call(var_dict["main_window"], 7)
            LOG.info("Listing Users.")
            menu_options[6] = u"7. Show List of Users ✓"
            menu_color[6] = curses.color_pair(7)
            var_dict["list_of_users"] = entries
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 6) + 6, 0,
                                           "List of Users",
                                           curses.A_BOLD | curses.A_UNDERLINE |
                                           curses.color_pair(8))
            display_list_with_numbers_test(var_dict["main_window"],
                                           int(screen_dims[0] / 6) + 7,
                                           0, entries)
            var_dict["main_window"].refresh()
            end_menu_call(var_dict["main_window"], 7)
        else:
            menu_color[6] = curses.color_pair(3)
            err_msg = "Unable to retrieve users"
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2) - 2,
                                           int(screen_dims[1] / 2) - int(len(
                                               err_msg) / 2),
                                           err_msg,
                                           curses.color_pair(
                                               3) | curses.A_BOLD)
            end_menu_call(var_dict["main_window"], 7)

    def menu_get_specific_user(self):
        screen_dims = setup_menu_call(var_dict["main_window"],
                                      "8. Get a Specific User")
        if self._check_user_config_dict(screen_dims):
            if "list_of_users" not in var_dict:
                self.menu_check_user_tree_dn_show_users()
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 6) + 6, 0,
                                           "List of Users",
                                           curses.A_BOLD | curses.A_UNDERLINE |
                                           curses.color_pair(8))
            display_list_with_numbers_test(var_dict["main_window"],
                                           int(screen_dims[0] / 6) + 7,
                                           0, var_dict["list_of_users"])
            var_dict["main_window"].refresh()
            user_dn = configuration_dict["user_tree_dn"]
            user_id_attribute = configuration_dict["user_id_attribute"]
            object_class = configuration_dict["user_object_class"]
            user_name_attribute = configuration_dict["user_name_attribute"]
            name_msg_prompt = "What is the user name you would like to get?"
            name = my_raw_input(var_dict["main_window"],
                                int(screen_dims[0] / 6) + 3,
                                int(screen_dims[1] / 2) - len(name_msg_prompt),
                                name_msg_prompt)
            try:
                entry = self.ldap_service.get_entry(user_dn,
                                                   user_id_attribute,
                                                   object_class,
                                                   user_name_attribute,
                                                   name)
            except conn_service.LDAPQueryException as e:
                menu_color[7] = curses.color_pair(3)
                limited_addstr(var_dict["main_window"],
                               int(screen_dims[0] / 2) - 2,
                               int(screen_dims[1] / 2) - int(len(str(e)) / 2),
                               str(e), curses.color_pair(3) | curses.A_BOLD)
                end_menu_call(var_dict["main_window"], 8)
            LOG.info("Successfully retrieved specific user.")
            menu_options[7] = u"8. Get a Specific User ✓"
            menu_color[7] = curses.color_pair(7)
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 6) + 5, 0,
                                           "User: "
                                           "{usr}".format(usr=name),
                                           curses.A_UNDERLINE | curses.A_BOLD |
                                           curses.color_pair(8))
            display_list_with_numbers(var_dict["main_window"],
                                      int(screen_dims[0] /
                                          6) + 6,
                                      0, entry)
            end_menu_call(var_dict["main_window"], 8)

    def menu_input_group_attributes(self):
        screen_dims = setup_menu_call(
            var_dict["main_window"],
            "9. Input Group ID Attribute/Group Name Attribute")
        if var_dict["conn"] == "none":
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2),
                                           int(screen_dims[1] / 2) - 23,
                                           "No LDAP server found. "
                                           "Press any key to go to the menu.")
            var_dict["main_window"].getch()
            display_menu()
        else:
            LOG.info("Prompting for group info.")
            group_id_attr_prompt = "What is the group id attribute?"
            group_name_attr_prompt = "What is the group name attribute?"
            group_tree_dn_prompt = \
                "What is the group tree DN, " \
                "not including the base DN (e.g. ou=Groups)?"

            if "suffix" in configuration_dict:
                group_tree_dn = my_raw_input(
                    var_dict["main_window"],
                    int(screen_dims[0] / 6) + 4,
                    int(screen_dims[1] / 2) - int(
                        len(group_tree_dn_prompt) / 2),
                    group_tree_dn_prompt)
                group_id_attribute = my_raw_input(
                    var_dict["main_window"],
                    int(screen_dims[0] / 6) + 6,
                    int(screen_dims[1] / 2) - int(
                        len(group_tree_dn_prompt) / 2),
                    group_id_attr_prompt)
                group_name_attribute = my_raw_input(
                    var_dict["main_window"],
                    int(screen_dims[0] / 6) + 8,
                    int(screen_dims[1] / 2) - int(
                        len(group_tree_dn_prompt) / 2),
                    group_name_attr_prompt)
            else:
                limited_addstr(var_dict["main_window"],
                    int(screen_dims[0] / 2), int(screen_dims[1] / 2) - 29,
                    "No Suffix (base DN) found. Press any key to go to the menu.")
                var_dict["main_window"].getch()
                display_menu()
            attempt_message = "Verifying information... Please wait."
            blank_message = "                                     "
            limited_addstr(var_dict["main_window"],
                int(screen_dims[0] / 6) + 17,
                int(screen_dims[1] / 2) - int(len(attempt_message) / 2),
                attempt_message,
                curses.color_pair(5))

            var_dict["main_window"].refresh()
            try:
                msg = self.ldap_service.validate_info(group_tree_dn + "," +
                                                 configuration_dict["suffix"],
                                                 group_id_attribute,
                                                 group_name_attribute)
            except conn_service.LDAPQueryException as e:
                limited_addstr(var_dict["main_window"],
                               int(screen_dims[0] / 6) + 17,
                               int(screen_dims[1] / 2) - int(
                                   len(attempt_message) / 2), blank_message)
                menu_color[8] = curses.color_pair(3)
                limited_addstr(var_dict["main_window"],
                           int(screen_dims[0] / 6) + 11,
                           int(screen_dims[1] / 2) - int(
                               len(str(e)) / 2), str(e),
                           curses.color_pair(3) | curses.A_BOLD)
                end_menu_call(var_dict["main_window"], 9)
            limited_addstr(var_dict["main_window"],
                           int(screen_dims[0] / 6) + 17,
                           int(screen_dims[1] / 2) - int(
                               len(attempt_message) / 2), blank_message)
            var_dict["main_window"].refresh()
            configuration_dict["group_id_attribute"] = group_id_attribute
            configuration_dict["group_name_attribute"] = group_name_attribute
            configuration_dict["group_tree_dn"] = \
                group_tree_dn + "," + configuration_dict["suffix"]
            show_console_in_status_window()
            menu_options[8] = \
                u"9. Input Group ID Attribute/Group Name Attribute ✓"
            menu_color[8] = curses.color_pair(7)
            limited_addstr(var_dict["main_window"],
                           int(screen_dims[0] / 6) + 11,
                           int(screen_dims[1] / 2) - int(len(msg) / 2),
                           msg, curses.color_pair(6) | curses.A_BOLD)
            update_message = "Configuration has been updated with this " \
                             "information."
            limited_addstr(var_dict["main_window"],
                int(screen_dims[0] / 6) + 12,
                int(screen_dims[1] / 2) - int(len(update_message) / 2),
                update_message, curses.color_pair(6) | curses.A_BOLD)
            end_menu_call(var_dict["main_window"], 9)

    def menu_show_list_group_object_classes(self):
        screen_dims = setup_menu_call(
            var_dict["main_window"],
            "10. Show List of Group Related ObjectClasses")
        if self._check_group_config_dict(screen_dims):
            conn = var_dict["conn"]
            group_dn = configuration_dict["group_tree_dn"]
            group_id_attribute = configuration_dict["group_id_attribute"]
            try:
                obj_classes = self.ldap_service.list_object_classes(group_dn, group_id_attribute)
            except conn_service.LDAPQueryException as e:
                menu_color[9] = curses.color_pair(3)
                err_msg = "Unable to retrieve group object classes"
                limited_addstr(var_dict["main_window"],
                               int(screen_dims[0] / 2) - 2,
                               int(screen_dims[1] / 2) - int(len(err_msg) / 2),
                               err_msg,
                               curses.color_pair(3) | curses.A_BOLD)
                end_menu_call(var_dict["main_window"], 10)

            LOG.info("Displaying group object classes.")
            object_classes_list = obj_classes + ["None of the above"]
            display_list_with_numbers(var_dict["main_window"],
                                      int(screen_dims[0] / 6) + 5,
                                      int(screen_dims[1] / 2) - 15,
                                      object_classes_list)
            num_obj_classes = len(object_classes_list)
            choice = my_numb_input(
                var_dict["main_window"],
                int(screen_dims[0] / 6) + num_obj_classes + 5,
                int(screen_dims[1] / 2) - 15,
                "Please choose one of the above.", num_obj_classes)
            if choice == num_obj_classes:
                group_obj_class = my_raw_input(
                    var_dict["main_window"],
                    int(screen_dims[0] / 6) + num_obj_classes + 7,
                    int(screen_dims[1] / 2) - 15,
                    "Please enter the group object class")
                try:
                    msg = self.ldap_service.validate_object_class(group_dn, group_obj_class)
                    color = 6
                    configuration_dict["group_object_class"] = group_obj_class
                    end_message = "{} has been added to configuration.".format(
                        group_obj_class)
                    limited_addstr(var_dict["main_window"],
                                   int(screen_dims[0] / 2) - 4,
                                   int(screen_dims[1] / 2) - int(len(
                                       end_message) / 2),
                                   end_message,
                                   curses.color_pair(6) |
                                   curses.A_BOLD)
                except conn_service.LDAPQueryException as e:
                    msg = str(e)
                    color = 3
                limited_addstr(var_dict["main_window"],
                    int(screen_dims[0] / 2) - 3,
                    int(screen_dims[1] / 2) - int(len(msg) / 2), msg,
                    curses.color_pair(color) | curses.A_BOLD)
                end_menu_call(var_dict["main_window"], 10)
            else:
                group_obj_class = str(object_classes_list[choice - 1])
                configuration_dict["group_object_class"] = group_obj_class
            end_message = "{} has been added to configuration.".format(group_obj_class)
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2) - 4,
                                           int(screen_dims[1] / 2) - int(len(
                                               end_message) / 2),
                                           end_message,
                                           curses.color_pair(6) |
                                           curses.A_BOLD)
            show_console_in_status_window()
            menu_options[9] = u"10. Show List of Group Related ObjectClasses ✓"
            menu_color[9] = curses.color_pair(7)
            end_menu_call(var_dict["main_window"], 10)

    def menu_check_group_tree_dn_show_groups(self):
        screen_dims = setup_menu_call(
            var_dict["main_window"],
            "11. Show List of Groups")
        if self._check_group_config_dict(screen_dims):
            conn = var_dict["conn"]
            group_dn = configuration_dict["group_tree_dn"]
            group_id_attribute = configuration_dict["group_id_attribute"]
            group_name_attribute = configuration_dict["group_name_attribute"]
            object_class = configuration_dict["group_object_class"]
            maximum = screen_dims[0] - int(screen_dims[0] / 6) - 7
            limit_prompt = "How many groups would you like to see? Maximum: {" \
                           "max}".format(max=maximum)
            limit = my_numb_input(
                var_dict["main_window"],
                int(screen_dims[0] / 6) + 4, int(screen_dims[1] / 2) - int(len(
                    limit_prompt) / 2),
                limit_prompt)
            limit = min(limit, maximum)
            try:
                entries = self.ldap_service.list_entries(group_dn,
                                                      group_id_attribute,
                                                      group_name_attribute,
                                                      object_class, limit)
            except conn_service.LDAPQueryException as e:
                menu_color[6] = curses.color_pair(3)
                limited_addstr(var_dict["main_window"],
                               int(screen_dims[0] / 2) - 2,
                               int(screen_dims[1] / 2) - int(len(str(e)) / 2),
                               str(e),
                               curses.color_pair(3) | curses.A_BOLD)
                end_menu_call(var_dict["main_window"], 11)

            LOG.info("Listing groups.")
            menu_options[10] = u"11. Show List of Groups ✓"
            menu_color[10] = curses.color_pair(7)
            var_dict["list_of_groups"] = entries
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 6) + 6, 0,
                                           "List of Groups",
                                           curses.A_BOLD | curses.A_UNDERLINE |
                                           curses.color_pair(8))
            display_list_with_numbers_test(var_dict["main_window"],
                                           int(screen_dims[0] / 6) + 7, 0,
                                           entries)
            end_menu_call(var_dict["main_window"], 11)
        else:
            menu_color[10] = curses.color_pair(3)
            err_msg = "Unable to retrieve groups"
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2) - 2,
                                           int(screen_dims[1] / 2) - int(len(
                                               err_msg) / 2),
                                           err_msg,
                                           curses.color_pair(
                                               3) | curses.A_BOLD)
            end_menu_call(var_dict["main_window"], 11)

    def menu_get_specific_group(self):
        screen_dims = setup_menu_call(var_dict["main_window"],
                                      "12. Get Specific Group")
        if self._check_group_config_dict(screen_dims):
            if "list_of_groups" not in var_dict:
                self.menu_check_group_tree_dn_show_groups()
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 6) + 6, 0,
                                           "List of Groups",
                                           curses.A_BOLD | curses.A_UNDERLINE)
            display_list_with_numbers_test(var_dict["main_window"],
                                           int(screen_dims[0] / 6) + 7, 0,
                                           var_dict["list_of_groups"])
            var_dict["main_window"].refresh()
            group_dn = configuration_dict["group_tree_dn"]
            group_id_attribute = configuration_dict["group_id_attribute"]
            object_class = configuration_dict["group_object_class"]
            group_name_attribute = configuration_dict["group_name_attribute"]
            name_msg_prompt = "What is the group name you would like to get?"
            name = my_raw_input(var_dict["main_window"],
                                int(screen_dims[0] / 6) + 3,
                                int(screen_dims[1] / 2) - len(name_msg_prompt),
                                name_msg_prompt)
            try:
                entry = self.ldap_service.get_entry(group_dn, group_id_attribute,
                                               object_class, group_name_attribute, name)
            except conn_service.LDAPQueryException as e:
                menu_color[7] = curses.color_pair(3)
                limited_addstr(var_dict["main_window"],
                               int(screen_dims[0] / 2) - 2,
                               int(screen_dims[1] / 2) - int(len(str(e)) / 2),
                               str(e), curses.color_pair(3) | curses.A_BOLD)
                end_menu_call(var_dict["main_window"], 12)
            LOG.info("Getting specific group.")
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 6) + 5, 0,
                                           "Group: "
                                           "{grp}".format(grp=name),
                                           curses.A_UNDERLINE | curses.A_BOLD |
                                           curses.color_pair(8))
            display_list_with_numbers(var_dict["main_window"],
                                      int(screen_dims[0] / 6) + 6,
                                      0, entry)
            menu_options[11] = u"12. Get Specific Group ✓"
            menu_color[11] = curses.color_pair(7)
            end_menu_call(var_dict["main_window"], 12)
        else:
            menu_color[11] = curses.color_pair(3)
            err_msg = "Unable to retrieve group"
            limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2) - 2,
                                           int(screen_dims[1] / 2) - int(len(
                                               err_msg) / 2),
                                           err_msg,
                                           curses.color_pair(
                                               3) | curses.A_BOLD)
            end_menu_call(var_dict["main_window"], 12)

    def menu_additional_config_options(self):
        LOG.info("Prompting for additional configuration options.")
        screen_dims = setup_menu_call(var_dict["main_window"],
                                      "13. Add Additional Configuration Options")

        tls_req_cert_prompt = \
            "What is tls_req_cert? (demand/never/allow) Default: demand"

        use_pool_prompt = "What is use_pool? This is for LDAP connection " \
                          "pooling. (" \
                          "True/False)"

        use_auth_pool_prompt = "What is use_auth_pool? (True/False) Default: True"

        if "tls_cacertfile" in configuration_dict:
            use_tls_prompt = "What is use_tls? (True/False) Default: True"
            default_use_tls = "True"
        else:
            use_tls_prompt = "What is use_tls? (True/False) Default: False"
            default_use_tls = "False"

        use_tls_string = my_raw_input(
            var_dict["main_window"], int(screen_dims[0] / 6) + 4,
                                     int(screen_dims[1] / 2) - int(
                                         len(use_tls_prompt) / 2),
            use_tls_prompt, default_use_tls)
        if use_tls_string in ("True", "t", "T", "true"):
            use_tls_string = True
        elif use_tls_string in ("False", "false", "f", "F"):
            use_tls_string = False
        while use_tls_string not in (True, False):
            limited_addstr(var_dict["main_window"],
                           int(screen_dims[0] / 6) + 5,
                           int(screen_dims[1] / 2) -
                           int(len(use_tls_prompt) / 2),
                           "                                 ")
            use_tls_string = my_raw_input(
                var_dict["main_window"], int(screen_dims[0] / 6) + 4,
                                         int(screen_dims[1] / 2) - int(
                                             len(use_tls_prompt) / 2),
                use_tls_prompt,
                default_use_tls)
            if use_tls_string in ("True", "t", "T", "true"):
                use_tls_string = True
            elif use_tls_string in ("False", "false", "f", "F"):
                use_tls_string = False
        configuration_dict["use_tls"] = use_tls_string
        show_console_in_status_window()

        tls_req_cert = my_raw_input(
            var_dict["main_window"], int(screen_dims[0] / 6) + 8,
                                     int(screen_dims[1] / 2) - int(
                                         len(tls_req_cert_prompt) / 2),
            tls_req_cert_prompt, "demand")
        while tls_req_cert not in ("demand", "allow", "never"):
            limited_addstr(var_dict["main_window"],
                           int(screen_dims[0] / 6) + 9,
                           int(screen_dims[1] / 2) -
                           int(len(tls_req_cert_prompt) / 2),
                           "                                  ")
            tls_req_cert = my_raw_input(
                var_dict["main_window"], int(screen_dims[0] / 6) + 8,
                                         int(screen_dims[1] / 2) - int(
                                             len(tls_req_cert_prompt) / 2),
                tls_req_cert_prompt, "demand")
        configuration_dict["tls_req_cert"] = tls_req_cert
        show_console_in_status_window()

        use_pool = my_raw_input(
            var_dict["main_window"], int(screen_dims[0] / 6) + 12,
                                     int(screen_dims[1] / 2) - int(
                                         len(use_pool_prompt) / 2),
            use_pool_prompt)
        if use_pool in ("True", "t", "T", "true"):
            use_pool = True
        elif use_pool in ("False", "false", "f", "F"):
            use_pool = False
        while use_pool not in (True, False):
            limited_addstr(var_dict["main_window"],
                           int(screen_dims[0] / 6) + 13,
                           int(screen_dims[1] / 2) -
                           int(len(use_pool_prompt) / 2),
                           "                                 ")
            use_pool = my_raw_input(
                var_dict["main_window"], int(screen_dims[0] / 6) + 12,
                                         int(screen_dims[1] / 2) - int(
                                             len(use_pool_prompt) / 2),
                use_pool_prompt)
            if use_pool in ("True", "t", "T", "true"):
                use_pool = True
            elif use_pool in ("False", "false", "f", "F"):
                use_pool = False
        configuration_dict["use_pool"] = use_pool
        show_console_in_status_window()

        use_auth_pool = my_raw_input(
            var_dict["main_window"], int(screen_dims[0] / 6) + 16,
                                     int(screen_dims[1] / 2) - int(
                                         len(use_auth_pool_prompt) / 2),
            use_auth_pool_prompt)
        if use_auth_pool in ("True", "t", "T", "true"):
            use_auth_pool = True
        elif use_auth_pool in ("False", "false", "f", "F"):
            use_auth_pool = False
        while use_auth_pool not in (True, False):
            limited_addstr(var_dict["main_window"],
                           int(screen_dims[0] / 6) + 17,
                           int(screen_dims[1] / 2) -
                           int(len(use_auth_pool_prompt) / 2),
                           "                                 ")
            use_auth_pool = my_raw_input(
                var_dict["main_window"], int(screen_dims[0] / 6) + 16,
                                         int(screen_dims[1] / 2) - int(
                                             len(use_auth_pool_prompt) / 2),
                use_auth_pool_prompt)
            if use_auth_pool in ("True", "t", "T", "true"):
                use_auth_pool = True
            elif use_auth_pool in ("False", "false", "f", "F"):
                use_auth_pool = False
        configuration_dict["use_auth_pool"] = use_auth_pool
        show_console_in_status_window()

        menu_color[12] = curses.color_pair(7)
        menu_options[12] = u"13. Add Additional Configuration Options ✓"
        end_menu_call(var_dict["main_window"], 13)

    def menu_create_config(self):
        screen_dims = setup_menu_call(var_dict["main_window"],
                                      "14. Save/Create Configuration File")
        data = configuration_dict
        string_prompt = "Please specify a file name."

        name_prompt = "Please speficy a domain name."
        name = my_raw_input(var_dict["main_window"],
                            int(screen_dims[0] / 2) - 2,
                            int(screen_dims[1] / 2) - int(
                                len(name_prompt) / 2),
                            name_prompt)
        path = my_raw_input(var_dict["main_window"], int(screen_dims[0] / 2),
                            int(screen_dims[1] / 2) - int(
                                len(string_prompt) / 2),
                            string_prompt)
        self.hos_yaml = conn_service.HOSYamlDump()
        try:
            return_msg = self.hos_yaml.save_config(data, path, name)
            menu_options[13] = u"14. Save/Create Configuration File ✓"
            menu_color[13] = curses.color_pair(7)
        except IOError as e:
            menu_color[13] = curses.color_pair(3)
            return_msg = str(e)

        limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2) - 4,
                                       int(screen_dims[1] / 2) - int(len(
                                           return_msg) / 2),
                                       return_msg)
        end_msg = "Press m to go to the menu."
        limited_addstr(var_dict["main_window"], int(screen_dims[0] / 2) - 3,
                                       int(screen_dims[1] / 2) - int(len(
                                           end_msg) / 2), end_msg)
        c = var_dict["main_window"].getch()
        while c != 109:
            if c == curses.KEY_RESIZE:
                resize_windows()
            c = var_dict["main_window"].getch()
        if c == 109:
            display_menu()


if __name__ == '__main__':
    m = Menu_Steps()
    LOG = logging.getLogger(__name__)
    timestamp_string = str(time.strftime('%B_%d_%Y_%X'))
    LOG.info("Setting up standard screen.")
    locale.setlocale(locale.LC_ALL, "")  # for unicode support
    stdscr = curses.initscr()  # terminal screen
    stdscr_dimensions = klct_curses_setup(stdscr)
    menu_color = [curses.color_pair(2)] * len(menu_options)
    LOG.info("Setting up status window.")
    status_window = stdscr.subwin(stdscr_dimensions[0] - 2,
                                  int(stdscr_dimensions[1] / 3) - 2, 1,
                                  stdscr_dimensions[1] -
                                  int(stdscr_dimensions[1] / 3))
    status_window.scrollok(True)
    status_window_text = stdscr.subwin(stdscr_dimensions[0] - 3,
                                       int(stdscr_dimensions[1] / 3) - 4, 2,
                                       stdscr_dimensions[1] -
                                       int(stdscr_dimensions[1] / 3) + 1)
    LOG.info("Setting up main screen")
    main_window = stdscr.subwin(stdscr_dimensions[0] - 2,
                                stdscr_dimensions[1] -
                                int(stdscr_dimensions[1] / 3) - 1, 1, 1)
    main_window.keypad(True)
    var_dict = {"conn": "none",
                "server": "none",
                "object_class": "none",
                "status_window": status_window,
                "status_window_text": status_window_text,
                "main_window": main_window,
                "port_added": False}
    configuration_dict = OrderedDict()
    curses.wrapper(show_instructions)
    curses.endwin()

