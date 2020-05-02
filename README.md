# Home Assistant System Tray
A system tray quick menu for Home Assistant and Blue Iris

This is a quick system tray app for toggling stuff in Home Assistant and popping up camera views without having to navigate a webpage.
I can also handle popping up a camera view based on an incoming MQTT topic, so home automation can pop up views upon events on any desktop machine you're running it on.  

Tested on Linux and Windows 10.

# Installation
Requires Python 3.7+
Download the repo and run the following command in the directory where you installed it:

`python -m pip install -r requirements.txt`

# Setup

Open up hass_systray.py in an editor and set up the URLs of your Home Assistant, MQTT, and Blue Iris servers.  Also add a long-lived access token from Home Assistant.

There are several different ways to add things to the menu.  The easiest two are to just list any entities and their names to the main menu.  
You can also add groups to the groups list.  Each group will be given it's own submenu, with the items in that group listed there.

Any item in these lists that is named "div" will create a dividing line between the entries in that group.
```
mainmenu = [
    {"name":"Couch Lamp",           "entity_id":"switch.couch_lamp" }, 
    {"name":"div",                  "entity_id":"div" },
    ]

groups = [
    "group.lights_floor_1",
    "group.lights_floor_2",
    "group.lights_floor_3"
    ]
```

Cameras require Blue Iris as it accesses them directly.  This is probably also possible with HASS, but I didn't try as it's easy to access them directly.  The 'name' is what will be shown in the menu and popup window, while 'id' is the shortname of the camera in Blue Iris. I haven't multithreaded anything yet, so currently windows which pop up a camera block further use of the app until they're closed.  You can close the window by pressing ESC or Space, and take a snapshot by pressing 's'.

```
cams = [
    {"name":"Front Door",           "id":"Turret" },
    {"name":"Driveway",             "id":"Dual1B" },
    {"name":"Front Walkway",        "id":"Dual1A" },
    ]
```

HassSystray will subscribe to a list of topics you give it.  It can then respond to these topics.  Currently all that's implemented is popping up a view of a camera you specify.  However, this can be expanded however you'd like...  

In the below setup, this will respond to a tasmota POWER topic and match the value of 'ON' (for a doorbell being pressed in this case) to pop up a specific camera on a desktop window for 10 seconds.  If the value in the MQTT message does not match 'ON', nothing will happen.

In the second example, it will respond to a specific systray command, and again popup the front door camera, but it does not try to match a value in the MQTT message, it will always work.

The third example matches the same parameters as the second, but the arguments are supplied by the MQTT message in the same json format, so the MQTT message will look like : cmnd/systray/viewcam  -  {"camera":"FrontDoor", "timeout":10}
Note if no timeout is specified, the window will stay up forever. 

```
# These three examples all do the same thing, the first one has a value_match, so the mqtt value received must be raw 'ON'
# The second one ignores the mqtt value and just brings up the specified camera for 10 seconds
# The third expects a json value to be specified which will include at least "camera" and optionally "timeout"
mqtt_subscriptions = [ 
    {'topic':'stat/sonoff_doorbell/POWER',      'func':view_cam,    'args':'{"value_match":"ON", "camera":"FrontDoor", "timeout":10}' },
    {'topic':'cmnd/systray/viewfrontdoor',      'func':view_cam,    'args':'{"camera":"FrontDoor", "timeout":10}' },
    {'topic':'cmnd/systray/viewcam',            'func':view_cam },
    ]
```

# Running

After you're done adding any entities or cameras, simply run the app in the background with :

`pyw -3 hass_systray.py`

or:

`py3 hass_systray.py&`

or however you run python3 on your system.


