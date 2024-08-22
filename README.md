SETUP INSTRUCTIONS
******************

MIDI PORTS:
1. Install loopMIDI or other virtual MIDI port software
2. Initialize a virtual MIDI port
3. When prompted to (when running the program), select this virtual MIDI port for I/O

REAPER:
1. Go to "Options->Preferences...->Audio->MIDI Devices"
2. In "MIDI inputs," ensure the virtual MIDI port appears in the Device list and that it is toggled on for "Input"
3. In "MIDI outputs," ensure the virtual MIDI port appears in the Device list and that it is toggled on for "Enable"
4. Create a new track
5. Set the input of this track to "Input: MIDI->[port name]->All Channels"
6. Open Plug Data in the FX of this track
7. Open "layout.pd"
8. Set the desired CC value of the output, as well as the Controller # and the Channel #
9. Create a new track for any plugin
10. In Routing for the plugin track, add a new receive from the Plug Data track
11. Set the audio input channel to "None"
12. Select the MIDI symbol
13. Set the output channel of the Plug Data track to the same as the Channel # in the patch
14. Open the plugin on the plugin track
15. To select the parameter to control, either press it on the plugin's GUI and then go to "Param->Parameter modulation/MIDI link'
    or go directly to "Param->Parameter modulation->MIDI link->[desired parameter]"
16. Check "Link from MIDI or FX parameter"
17. Click "(none)->MIDI->CC" and select the same number as the specified Controller # in Plug Data (disregard default associated names)
18. Repeat steps 8 to 17 for each new parameter to control, creating a new "ccout" abstraction for each one
