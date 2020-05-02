import wx.adv
import wx
import paho.mqtt.client as mqtt
import requests
import webbrowser
import cv2
import numpy as np
import tkinter
import PIL.Image, PIL.ImageTk
import time
import json

LONG_LIVED_ACCESS_TOKEN = '[YOUR_LONG_LIVED_ACCESS_TOKEN]'
BLUEIRIS_URL = 'http://[YOUR_BLUE_IRIS_IP_OR_URL]'
HOMEASSISTANT_URL = 'http://[YOUR_HASS_IP_OR_URL]'
MQTT_URL = '[YOUR_MQTT_IP_OR_URL]'
TRAY_TOOLTIP = 'Home Assistant' 
TRAY_ICON = 'https://www.home-assistant.io/images/supported_brands/home-assistant.png' 


# Anything listed here will go on the main menu.  Groups listed will be treated as one
# "div" will place a divider
mainmenu = [
    #{"name":"Couch Lamp",           "entity_id":"switch.couch_lamp" }, 
    #{"name":"div",                  "entity_id":"div" },
    ]

# Any groups listed here will be broken out into individual group items in submenus, friendly names are automatic
# If you have a bunch of groups you'd like to add, this is the easiest way
groups = [
    #"group.bedside_lights",
    #"group.lights_floor_2",
    #"group.lights_floor_3"
    ]

#groups here will be treated as one, all entitys are under a lights submenu
lights = [
    #{"name":"Couch Lamp",           "entity_id":"switch.couch_lamp" }, 
    #{"name":"Stairwell",            "entity_id":"group.lights_stairwell"},
    #{"name":"Loft",                 "entity_id":"light.loft_loft_lights" },
    #{"name":"Living Room",          "entity_id":"group.lights_livingroom" },
    #{"name":"Dining Room",          "entity_id":"light.dining_room_lights" },
    #{"name":"Kitchen",              "entity_id":"light.kitchen_lights" },
    #{"name":"div",                  "entity_id":"div" },
    #{"name":"1st Floor",            "entity_id":"group.lights_floor_1" },
    #{"name":"2nd Floor",            "entity_id":"group.lights_floor_2" },
    #{"name":"3rd Floor",            "entity_id":"group.lights_floor_3" },
    #{"name":"4th Floor",            "entity_id":"group.lights_floor_4" },
    #{"name":"All Lights",           "entity_id":"group.lights" },
    ]

# Blue Iris cameras - id must match the short name specified in Blue Iris
cams = [
    #{"name":"Front Door",           "id":"FrontDoor" },
    #{"name":"Driveway",             "id":"Dual1B" },
    #{"name":"Front Walkway",        "id":"Dual1A" },
    #{"name":"Garbage Bins",         "id":"Dual2A" },
    #{"name":"Back Walkway",         "id":"Dual2B" },
    #{"name":"Garage",               "id":"Garage" },
    ]

# MQTT Functions
# These are called from the below subscriptions
# Customize thse are necessary

# View Camera - json format is {'camera':'[camname]', 'timeout':[secs]}
# if args value_match is specified raw mqtt value must match - ie 'ON', before it'll override the value, otherwise args always override
def view_cam( value, args = None ):
    timeout = None
    if args is not None and is_json(args):
        json_value = json.loads(args)
        if 'value_match' in json_value:
            # Check to see if our value matches, otherwise, abort
            if json_value['value_match'] == value:
                value = args
            else:
                return
        else:
            value = args
    if is_json( value ): 
        json_value = json.loads(value)
        cam = json_value['camera']
        if "timeout" in json_value:
            timeout = json_value['timeout']
    else:
        return
    VidWin(tkinter.Tk(), "Live View", video_source=BLUEIRIS_URL+'/mjpg/'+cam+'/video.mjpg', timeout=timeout )

# These three examples all do the same thing, the first one has a value_match, so the mqtt value received must be raw 'ON'
# The second one ignores the mqtt value and just brings up the specified camera for 10 seconds
# The third expects a json value to be specified which will include at least "camera" and optionally "timeout"
mqtt_subscriptions = [ 
    {'topic':'stat/sonoff_doorbell/POWER',      'func':view_cam,    'args':'{"value_match":"ON", "camera":"FrontDoor", "timeout":10}' },
    {'topic':'cmnd/systray/viewfrontdoor',      'func':view_cam,    'args':'{"camera":"FrontDoor", "timeout":10}' },
    {'topic':'cmnd/systray/viewcam',            'func':view_cam },
    ]




class TaskBarIcon(wx.adv.TaskBarIcon):
    def __init__(self, frame):
        self.frame = frame
        super(TaskBarIcon, self).__init__()
        # download our Icon if we don't already have it.
        try:
            png = PIL.Image.open("icon.png")
        except:
            png = PIL.Image.open(requests.get(TRAY_ICON, stream=True).raw)
            png.save( "tray_icon.png" )
        self.set_icon("tray_icon.png")
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)
        self.lights = lights
        self.cams = cams
        self.groups = groups
        self.mainmenu = mainmenu


    # Menu gets created here, you can add whatever additions easily here
    # See commented out examples
    def CreatePopupMenu(self):
        menu = wx.Menu()

        
        
        # Manual menu entries example      
        #create_menu_item_ex(menu, 'View Front Door', self.on_view_cam, self.cams[0] )
        #create_menu_item(menu, 'Couch Lamp', self.on_couch_lamp )
        #create_menu_item(menu, 'TV Time', self.on_tv_time )

        for ent in self.mainmenu:
            if ent["name"] == 'div':
                menu.AppendSeparator()
            else:
                create_menu_item_ex(menu, ent["name"], self.on_entity_toggle, ent["entity_id"] )
                
        # Create Submenus for all Groups
        for group in self.groups:
            if group == 'div':
                menu.AppendSeparator()
            else:
                url = HOMEASSISTANT_URL+'/api/states/'+group
                response = requests.get(url, headers=headers, timeout=1.50)
                if response is not None:
                    cur_state = response.json()
                    submenu = wx.Menu()
                    name = cur_state['attributes']['friendly_name']
                    menu.AppendSubMenu( submenu, name )
                    for ent in cur_state['attributes']['entity_id']:
                        url2 = HOMEASSISTANT_URL+'/api/states/'+ent
                        response2 = requests.get(url2, headers=headers, timeout=1.50)
                        if response2 is not None:
                            ent_state = response2.json()
                            if 'attributes' in ent_state:
                                create_menu_item_ex(submenu, ent_state['attributes']['friendly_name'], self.on_entity_toggle, ent )
                            else:
                                print( "BAD ENTITY IN GROUP: " + ent )
                    

        # Custom submenu exampe
        #fan = wx.Menu()
        #menu.AppendSubMenu(fan, 'Loft Fan')
        #create_menu_item_ex(fan, 'Toggle Fan Power', self.on_fan, "POWER")
        #create_menu_item_ex(fan, 'Toggle Fan Oscillate', self.on_fan, "OSCILLATE")
        #create_menu_item_ex(fan, 'Toggle Fan Ion', self.on_fan, "ION")        
        #create_menu_item_ex(fan, 'Toggle Fan Speed', self.on_fan, "FAN")     
        
        if len(self.lights) > 0:
            lights = wx.Menu()
            menu.AppendSubMenu(lights, 'Lights')
            for light in self.lights:
                if light["name"] == 'div':
                    lights.AppendSeparator()
                else:
                    item = create_menu_item_ex(lights, light["name"], self.on_entity_toggle, light["entity_id"] )

        if len(self.cams) > 0:  
            cams = wx.Menu()
            menu.AppendSubMenu(cams, 'Cameras' )
            for cam in self.cams:
                if cam["name"] == 'div':
                    cams.AppendSeparator()
                else:
                    create_menu_item_ex(cams, cam["name"], self.on_view_cam, cam )
            # Example of manual addition to automatic camera submenu
            #create_menu_item(cams, 'Restart Interior Door Cam', self.on_restart_interior_door_cam )
        
        create_menu_item(menu, 'Exit', self.on_exit)
        return menu

        
        
## Doing Stuff - Add any custom functions you need here:

    #default left mouse
    def on_left_down(self, event):  
        webbrowser.open(HOMEASSISTANT_URL, new = 2) 
        
    #MQTT Direct Example
    def on_couch_lamp(self, event):
         client.publish("cmnd/sonoff_couch_lamp/POWER",'toggle')
         
    #MQTT with an argument
    def on_fan(self, event, cmnd ):
         value = '{"Protocol":"Lasko","Command":"' +cmnd+'"}' 
         client.publish("cmnd/sonoff_fan_ir/IRSend", value )      
    
    #RESTful Direct Example
    def on_restart_interior_door_cam( self, event ):
        params = (('cmd', 'reboot'),)
        response = requests.get('http://192.168.0.106/cgi-bin/action', params=params)
    
    #Home Assistant RESTful API
    def on_tv_time( self, event):
        data = '{"entity_id": "script.tv_time"}'
        response = requests.post(HOMEASSISTANT_URL+'/api/services/script/turn_on', headers=headers, data=data)
    
    #Multiple hardcoded example
    def on_light_stairwell_off( self, event):
        data = '{"entity_id": "light.mid_stairwell_lights"}'
        response = requests.post(HOMEASSISTANT_URL+'/api/services/light/turn_off', headers=headers, data=data)       
        data = '{"entity_id": "light.upper_stairwell_lights"}'
        response = requests.post(HOMEASSISTANT_URL+'/api/services/light/turn_off', headers=headers, data=data)  
        data = '{"entity_id": "light.lower_stairwell_lights"}'
        response = requests.post(HOMEASSISTANT_URL+'/api/services/light/turn_off', headers=headers, data=data) 

    #Generic Entity Toggle
    def on_entity_toggle( self, event, entity ):
        data = '{"entity_id": "'+ entity + '" }'
        domain = entity.split(".", 1 )
        command = 'toggle'
        # Groups don't play nice with toggle via the API so we have to determine their state and do the right thing
        if domain[0] == "group":
            url = HOMEASSISTANT_URL+'/api/states/'+entity
            response = requests.get(url, headers=headers, timeout=1.50)
            cur_state = response.json()
            if cur_state["state"] == 'off':
                command = 'turn_on'
            else:
                command = 'turn_off'
        requests.post(HOMEASSISTANT_URL+'/api/services/homeassistant/'+command, headers=headers, data=data)   
    
    #Hard Coded Example
    def on_light_all_off( self, event):
        data = '{"entity_id": "group.lights"}'
        response = requests.post(HOMEASSISTANT_URL+'/api/services/light/turn_off', headers=headers, data=data)   
    
    #Camera
    def on_view_cam( self, event, cam ):
        VidWin(tkinter.Tk(), cam["name"], video_source=BLUEIRIS_URL+'/mjpg/' + cam["id"] + '/video.mjpg')

    def set_icon(self, path):
        icon = wx.Icon(path)
        self.SetIcon(icon, TRAY_TOOLTIP )
                
    def on_exit(self, event):
        wx.CallAfter(self.Destroy)
        self.frame.Close()

headers =   {'Authorization': 'Bearer ' + LONG_LIVED_ACCESS_TOKEN, 'Content-Type': 'application/json'}    
client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    # We'll subscribe to a generic system tray topic for receiving MQTT Commands
    client.subscribe("cmnd/systray/#")

    # Subscribe to any topics listed in our subscriptions
    for sub in mqtt_subscriptions:
        client.subscribe( sub["topic"] )
    
# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))
    for sub in mqtt_subscriptions:
        if sub["topic"] == msg.topic:
            if "args" in sub:
                sub["func"](str( msg.payload.decode("utf-8")), sub["args"] )
            else:    
                sub["func"](str( msg.payload.decode("utf-8")) )
            
def is_json( input ):
    if input[0] is not '{':
        return False
    try:
        json_object = json.loads(input)
        return True
    except ValueError as e:
        print( "Invalid JSON! : ")
        print( e )
        return False
    return False

class VidWin:
    def __init__(self, window, window_title, video_source=0, timeout = None):
        self.window = window
        self.window.title(window_title)
        self.video_source = video_source
        if timeout is not None:
            self.endtime = time.time() + timeout
        else:
            self.endtime = None

        self.vid = CamVideoCapture(self.video_source)

        # Create a canvas that can fit the above video source size
        self.canvas = tkinter.Canvas(window, width = self.vid.width, height = self.vid.height)
        self.canvas.pack()
        self.center( window )
        
        self.window.bind("<Escape>", self.close_window)
        self.window.bind("<space>", self.close_window)
        # S key will take a snapshot
        self.window.bind("s", self.snapshot)

        #15 MS update rate, push higher for lower CPU hit
        self.delay = 15
        self.update()

        self.window.mainloop()

    def snapshot(self):
        # Get a frame from the video source
        ret, frame = self.vid.get_frame()
        if ret:
            cv2.imwrite("frame-" + time.strftime("%d-%m-%Y-%H-%M-%S") + ".jpg", cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

    def update(self):
        # Get a frame from the video source
        if self.endtime is not None and time.time() > self.endtime:
            self.close_window()
            return
            
        ret, frame = self.vid.get_frame()

        if ret:
            img = PIL.Image.fromarray(frame)
            height = self.canvas.winfo_height()
            #Video is costly and scaling frames is too, so let's only do it if we have to
            if ( img.height * 2 <= height ):
                width = self.canvas.winfo_width()
                img =img.resize((width,height), PIL.Image.ANTIALIAS )
            self.photo = PIL.ImageTk.PhotoImage(image = img)
            self.canvas.create_image(0, 0, image = self.photo, anchor = tkinter.NW)

        self.window.after(self.delay, self.update)

    def close_window(self, event = None):
        self.window.destroy()
            

    def center(self, win):
        win.update_idletasks()
        width = win.winfo_width()
        frm_width = win.winfo_rootx() - win.winfo_x()
        win_width = width + 2 * frm_width
        height = win.winfo_height()
        titlebar_height = win.winfo_rooty() - win.winfo_y()
        win_height = height + titlebar_height + frm_width
        x = win.winfo_screenwidth() // 2 - win_width // 2
        y = win.winfo_screenheight() // 2 - win_height // 2
        win.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        win.deiconify()

class CamVideoCapture:
    def __init__(self, video_source=0):
        # Open the video source
        self.vid = cv2.VideoCapture(video_source)
        if not self.vid.isOpened():
            raise ValueError("Unable to open video source", video_source)

        # Get video source width and height
        width = self.vid.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT)
        
        #If our video is small relative to our screensize, let's go ahead and scale it up
        scr_width, scr_height = wx.GetDisplaySize() 
        if height * 2 < scr_height:
            width = width * 2
            height = height * 2
        self.width = width
        self.height = height
        

    def get_frame(self):
        if self.vid.isOpened():
            ret, frame = self.vid.read()
            if ret:
                # Return a boolean success flag and the current frame converted to BGR
                return (ret, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            else:
                return (ret, None)
        else:
            return (ret, None)

    # Release the video source when the object is destroyed
    def __del__(self):
        if self.vid.isOpened():
            self.vid.release()



def create_menu_item(menu, label, func):
    item = wx.MenuItem(menu, -1, label)
    menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    menu.Append(item)
    return item

def create_menu_item_ex(menu, label, func, arg):
    item = wx.MenuItem(menu, -1, label)
    menu.Bind(wx.EVT_MENU, lambda evt, temp=arg: func(evt, temp), id=item.GetId() )
    menu.Append(item)
    return item


class App(wx.App):
    def OnInit(self):
        frame=wx.Frame(None)
        self.SetTopWindow(frame)
        TaskBarIcon(frame)
        return True

def main():
    app = App(False)

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_URL, 1883, 60)
    client.loop_start()
    
    app.MainLoop()
    


if __name__ == '__main__':
    main()
