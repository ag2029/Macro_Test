import numpy as np
from artiq.experiment import *

class SuservoSet(EnvExperiment):
    """Configure SUServo RF/AOM outputs, optional feedback, and monitoring.

    The experiment exposes channel selection and output/feedback parameters
    in the ARTIQ GUI. Hardware-specific calibration values are documented
    alongside the settings that use them.
    """

# Artiq devices to use

def build(self):
        self.setattr_device("scheduler")  # gives access of ARTIQ scheduler to host PC
        self.setattr_device("core")  # home of the kernel, access to timing core and RTIO
        self.setattr_device("suservo0")  # SUServo class - TO USE, access to overall SUServo device
        self.setattr_device("suservo0_ch0")  # Channel class - TO USE, make channels available to the experiment
        self.setattr_device("suservo0_ch1")  # Channel class - TO USE
        self.setattr_device("suservo0_ch2")  # Channel class - TO USE
        self.setattr_device("suservo0_ch3")  # Channel class - TO USE
        self.setattr_device("suservo0_ch4")  # Channel class - TO USE NOW THE RFs DON'T USE ACCIDENTALLY
        self.setattr_device("suservo0_ch5")  # Channel class - TO USE
        self.setattr_device("suservo0_ch6")  # Channel class - TO USE
        self.setattr_device("suservo0_ch7")  # Channel class - TO USE
        # Channel indices: 0-7. Check the physical channel mapping before use.
        self.setattr_argument(
            "channel",
            NumberValue(0, min=0, max=7, step=1, scale=1, precision=0),
        )#channel is for the AOM channel
        self.setattr_argument(
            "channel_RF",
            NumberValue(1, min=0, max=7, step=1, scale=1, precision=0),
        )#channel_RF is for the RF channel
        # Optional hardware initialisation. Leave disabled for normal runs
        # unless the hardware requires reinitialisation.
        self.setattr_argument(
            "initialise",
            BooleanValue(False),
            group="initialisation",
        )
        
        # POSSIBLE FREQUENCY VALUES FOR RF
        self.setattr_argument(
            "frequency_RF",
            NumberValue(
                18.278119e6, min=1e6, max=400e6, step=0.1e3, scale=1e6, unit="MHz", precision=6),
            group="OUTPUT_RF",
        )
# POSSIBLE FREQUENCY VALUES FOR RF
        self.setattr_argument(
            "frequency_RF",
            NumberValue(18.278119e6, min=1e6, max=400e6, step=0.1e3, scale=1e6, unit="MHz", precision=6),
            group="OUTPUT_RF",
        )

 # POSSIBLE INITIAL AMPLITUDE VALUES
        self.setattr_argument(
            "initial_amplitude",
            NumberValue(0.3, min=0.3, max=1.0, step=0.01, scale=1, unit="/1", precision=3),
            group="OUTPUT_AOM",
        )

# POSSIBLE INITIAL AMPLITUDE VALUES FOR RF
        self.setattr_argument(
            "initial_amplitude_RF",
            NumberValue(160, min=10, max=250, step=0.01, scale=1, unit="mV", precision=3),
            group="OUTPUT_RF",
        )
"""HIgher attenuation values will reduce the output power."""
# POSSIBLE ATTENUATION VALUES
        self.setattr_argument(
            "attenuation",
            NumberValue(25, max=25, min=0, step=0, scale=1, unit="dB", precision=1),
            group="OUTPUT_AOM",
        )

# POSSIBLE ATTENUATION VALUES For RF
        self.setattr_argument(
            "attenuation_RF",
            NumberValue(7, max=25, min=7, step=0, scale=1, unit="dB", precision=1),
            group="OUTPUT_RF",
        )

# The following parameters configure the SUServo feedback controller.

        self.setattr_argument(
            "target_voltage",
            NumberValue(0.1, min=0.0, max=5.0, step=0.0001, unit="V", precision=5),
            group="feedback",
        )#seets the target voltage for the AOM feedback loop.
        #adc_gain is to amplify the error signal, which is the difference between the target voltage and the actual voltage.
        self.setattr_argument(
            "adc_gain",
            NumberValue(1, min=0, max=3, step=1, unit="(10^)", scale=1, precision=0),
            group="feedback",
        )
        #prop_gain is to give an immediate response to the error signal, proportional to the current error.
        self.setattr_argument(
            "prop_gain",
            NumberValue(
                -3.0, min=-100.0, max=0.0, step=0.001, scale=1, unit="/1", precision=5),
            group="feedback",
        )
        #int_gain eliminate steady state error
         self.setattr_argument(
            "intg_gain",
            NumberValue(
                -250.0, min=-30000.0, max=0.0, step=0.001, scale=1, unit="rad/s", precision=3),
            group="feedback",
        )
        #sets threshold for anti-windup clamping, which prevents the integral term from accumulating excessively when the actuator is saturated.    
        self.setattr_argument(
            "intg_limit",
            NumberValue(
                0.0, max=100.0, min=-100.0, step=0.01, scale=1, unit="/1", precision=2),
            group="feedback",
        )
        # its for enabling or disabling the feedback loop. 
        self.setattr_argument("feedback_on", BooleanValue(False), group="feedback")
        self.setattr_argument("feedback_on", BooleanValue(False), group="feedback")#its a checkbox in GUI for feedback
        self.setattr_argument(
            "sweep_on",
            EnumerationValue(["Off", "Frequency Sweep 70 to 140 MHz", "Strobe the AOM"]),
            "AOM Alignment Stuff",
        )# dropdown list in GUI for sweep options.
        self.frequency_sweep_on = False
        self.strobe_on = False
        if self.sweep_on == "Frequency Sweep 70 to 140 MHz":
            self.frequency_sweep_on = True
        elif self.sweep_on == "Strobe the AOM":
            self.strobe_on = True
        #frequencies for trapping runs.
        low = 95e6  # 70e6
        high = 108e6  # 140e6 changed values for initial trapping runs
        self.freqs = np.concatenate([np.linspace(low, high), np.linspace(low, high)[::-1]])
        # List the channels for ease of use
        self.suservo0_ch = [
            self.suservo0_ch0,
            self.suservo0_ch1,
            self.suservo0_ch2,
            self.suservo0_ch3,
            self.suservo0_ch4,
            self.suservo0_ch5,
            self.suservo0_ch6,
            self.suservo0_ch7,
        ]
def prepare(self):
        # do some bool to int casting of flags
        self.AttenuationRegister = self.get_dataset("suservo.att_reg", 0, archive=False)#load the register value from ARTIQ dataset
        self.switch_state = int(True)
        self.feedback_on = int(self.feedback_on)#convert the checkbox value of feedback from boolean to integer for the SUServo board
        # rescale from target voltage to servo offset.
        # Converts the desired target_voltage into the internal offset value
        # used by the servo (accounting for ADC gain scaling — a decade per gain step,
        #  and a factor of 10 for full-scale range).

        self.offset = -self.target_voltage / 10 * 10**self.adc_gain #convert the target voltage into ADC's measurement scale
        print(f"computed voltage offset in [-1,1] is {self.offset}")

        if self.channel != 0 and (self.frequency_sweep_on or self.strobe_on):
            raise ValueError("ITS DUMB TO USE AOM ALIGNMENT STUFF ON OTHER CHANNELS.")

        print(self.frequency_RF)
        # @rpc(flags={"async"})
    # def statusprint(self, status):
    #     print(f"SU enable: {status & 0b01:01b}")
    #     print(f"SU done: {(status >> 1) & 0b01:01b}")
    #     print(f"SU clip: {status >> 8:08b}")
    #
    # @rpc(flags={"async"})
    # def stringprint(self, s):
    #     print(f"SU: {s:s}")
    #
    # @rpc(flags={"async"})
    # def p1(self, adc, asf, st):
    #     print(f"x:{adc} y:{asf} s:{(st & 0b11):02b} c:{(st >> 8):08b}")
    #     print(
    #         "ADC: {:10s}, ASF: {:10s}, clipped: {}".format(
    #             "#" * int(adc * (10**self.adc_gain)),
    #             "#" * int(asf * 10),
    #             int(st >> (8 + self.channel) & 0b1),
    #         ),
    #         flush=True,
    #     )
"""Here the @rpc decorator is used by ARTIQ to call function from host pc to the core device."""
    @rpc(flags={"async"})  # check for termination request
    def sch_pause(self):
        self.scheduler.pause()  # allow termination or pause request
    @kernel
    def set_RF(self):  # This was a trial function and it's nor being used.
        self.core.break_realtime()

        # set frequency
        self.suservo0_ch[self.channel_RF].set_dds(profile=0, frequency=self.frequency_RF, offset=0.0)

        # set amplitude
        self.suservo0_ch[self.channel_RF].set_y(
            profile=0,
            y=(self.initial_amplitude_RF - 1) / 248,  # this is a calibration from amplitude to mV. V(a) = 248*a + 1 mV
        )

        # enable output, disable feedback
        self.suservo0_ch[self.channel_RF].set(en_out=1, en_iir=0, profile=0)

        @kernel
    def update_urukul_output(self):#The update_urukul_output() function is used to configure and update the RF output of a selected Urukul DDS channel through the SUServo system in ARTIQ.
        self.core.break_realtime()#ensures that subsequent operations are not scheduled in the past
        delay(80 * us)

        self.suservo0_ch[self.channel].set_dds(profile=0, frequency=self.frequency / 0.8, offset=self.offset)#The function then sets the DDS frequency, profile, and offset using set_dds()
        delay(80 * us)

        # self.suservo0.cpld0.set_att(channel=self.channel, att=self.attenuation) #cpld0 --> cplds[0]; artiq6 --> artiq7
        # Indexes the correct card
        #selects the appropriate CPLD and local channel based on the selected channel number
        if self.channel < 4:
            c_ch = 0
            u_ch = self.channel
        else:
            c_ch = 1
            u_ch = self.channel - 4

        self.suservo0.cplds[c_ch].set_att(channel=u_ch, att=self.attenuation)# applies the specified RF attenuation using set_att()
        delay(80 * us)
        self.suservo0_ch[self.channel].set_y(profile=0, y=self.initial_amplitude)#set_y() to update an amplitude-related parameter for the selected channel.
        delay(80 * us)

"""The update_urukul_output_RF() function is used to configure and control the RF output of a selected Urukul channel operating in SUServo mode in ARTIQ. 
It sets the DDS frequency and offset, selects the appropriate CPLD and channel, and, when the self.initialise option is enabled, sets the RF attenuation and 
gradually ramps the output amplitude to a predefined target corresponding to 160 mV. This gradual ramp helps avoid sudden changes in RF output that could disturb the trapped ion. 
After initialization, the function reads the current amplitude-related value using get_y() and gradually ramps it to the target calculated from self.initial_amplitude_RF. 
The ramp_y() function uses 100 steps over 10 milliseconds to provide a gradual transition rather than an abrupt amplitude change. Overall, this function initializes and updates 
the RF output frequency, attenuation, and amplitude-related settings while aiming to minimize sudden RF changes that could affect the ion trap experiment."""
    @kernel
    def update_urukul_output_RF(self):
        # This function controls the RF output from the Urkul board in Suservo mode.
        # It sets the frequency, amplitude, and attenuation for the specified RF channel.
        # It has an initialisation option for the attenuation, if the attenuation is always the same,
        # 7db, there is no need to change.
        # Also the set_att function will drop the RF output for a shoert time before going to the new value,
        # dropping the ion.

        self.core.break_realtime()
        delay(80 * us)

        self.suservo0_ch[self.channel_RF].set_dds(profile=0, frequency=self.frequency_RF / 0.8, offset=self.offset)
        delay(80 * us)

        # self.suservo0.cpld0.set_att(channel=self.channel, att=self.attenuation) #cpld0 --> cplds[0]; artiq6 --> artiq7

        # Indexes the correct card
        if self.channel_RF < 4:
            c_ch = 0
            u_ch = self.channel_RF
        else:
            c_ch = 1
            u_ch = self.channel_RF - 4
        # When initialise we set a voltage for RF channel and attenuation
        if self.initialise:
            self.suservo0.cplds[c_ch].set_att(channel=u_ch, att=self.attenuation_RF)
            delay(80 * us)
            ##Fixed TARGET value for initialisation,160mV is the target voltage for RF channel
            y_target = (160.0 - 1.0) / 248.0
            y_start = 0.0
            # fixed ramp time and steps for initialisation, can be changed if needed
            self.ramp_y(
                ch=self.channel_RF, profile=0, y_start=y_start, y_target=y_target, ramp_time=10000 * us, steps=100
            )

        delay(80 * us)
        y_target = (self.initial_amplitude_RF - 1.0) / 248.0
        y_start = self.suservo0_ch[self.channel_RF].get_y(0)
        self.ramp_y(ch=self.channel_RF, profile=0, y_start=y_start, y_target=y_target, ramp_time=10000 * us, steps=100)
        # self.suservo0_ch[self.channel_RF].set_y(profile=0, y=(self.initial_amplitude_RF - 1) / 248)
        delay(80 * us)    
"""The update_urukul_feedback() function is used to configure the feedback system for a selected Urukul channel operating in SUServo mode in ARTIQ. 
It first prepares the real-time timeline using self.core.break_realtime() and introduces short delays between hardware operations. It then configures the gain of the ADC input amplifier using set_pgia_mu(), 
which determines how strongly the feedback signal is amplified before measurement. Next, the function configures an infinite impulse response (IIR) feedback controller using set_iir(), specifying the ADC channel, 
proportional gain (kp), integral gain (ki), integral limit (g), and feedback delay. The proportional gain determines how strongly the controller responds to the current error, while the integral gain helps correct 
persistent errors over time. The integral limit constrains the integral contribution, and delay=0.0 specifies no additional delay in the controller configuration. Overall, this function prepares the measurement and 
feedback-control settings that allow SUServo to monitor the RF signal and adjust its output to maintain the desired operating condition."""
    @kernel
    def update_urukul_feedback(self):
        self.core.break_realtime()
        delay(80 * us)
        # setup ADC amplifier gain 0=1x, 1=10x, 2=100x, 3=1000x
        # assume matching urukul & sampler channels (not strictly required)
        self.suservo0.set_pgia_mu(self.channel, self.adc_gain)
        delay(80 * us)
        self.suservo0_ch[self.channel].set_iir(
            profile=0,
            adc=self.channel,
            kp=self.prop_gain,
            ki=self.intg_gain,
            g=self.intg_limit,
            delay=0.0,
        )
        delay(80 * us)
"""The `ramp_y()` function is used to gradually increase or decrease the DDS amplitude scale of a selected SUServo channel from a starting
value to a target value over a specified time. It first prepares the ARTIQ real-time timeline using `self.core.break_realtime()` and calculates
the duration of each step by dividing the total ramp time by the number of steps. The function then uses a `for` loop to calculate intermediate 
amplitude values through linear interpolation, ensuring that the amplitude changes smoothly rather than jumping directly to the target. It also 
checks that each value remains within the valid range of 0 to just below 1 to prevent invalid values and potential overflow. At each step, `set_y()`
applies the calculated amplitude scale to the selected channel and profile, followed by a short delay before the next update. By default, the function 
performs 100 steps over 10 milliseconds, helping to reduce sudden changes in RF amplitude that could disturb the trapped ion during an experiment."""
    @kernel
    def ramp_y(self, ch, profile, y_start, y_target, ramp_time=10000 * us, steps=100):
        """
        Ramps a channel's y (DDS amplitude scale) from its current value
        to y_target over ramp_time, in `steps` linear increments.
        """
        self.core.break_realtime()
        step_time = ramp_time / steps
        for i in range(steps + 1):
            y = y_start + (y_target - y_start) * (i / steps)
            # y must stay within valid full-scale range [0, 1)
            if y < 0.0:
                y = 0.0
            if y > 0.999969:  # just under 1.0, avoids the 17-bit overflow edge
                y = 0.999969
            self.suservo0_ch[ch].set_y(profile, y)
            delay(step_time)
"""The monitor_loop() function is used to continuously monitor the feedback signal from the selected SUServo channel in an ARTIQ experiment. It first initializes
 a dataset named "SUServo.Sampler.reading" with 300 zero values so that the readings can be stored and accessed by other parts of the experiment or displayed in a 
 monitoring interface. Inside the infinite while True loop, it temporarily stops the SUServo configuration, reads the ADC value using get_adc() to measure the feedback
signal, retrieves the current DDS amplitude scale using get_y() for profile 0, and reads the servo status using get_status(). It then restarts the SUServo configuration 
and updates the dataset with the latest ADC reading using mutate_dataset(), replacing one value at index j % 300 so that the dataset retains a rolling buffer of the most 
recent 300 readings. The variable j increments after each measurement, and delay(0.05 * s) introduces a 50-millisecond pause between monitoring cycles, where s is the time
unit in seconds. Finally, sch_pause() checks whether the ARTIQ scheduler has requested the experiment to pause or yield control. Overall, this function provides continuous 
monitoring of the SUServo feedback signal, allowing the signal to be observed over time while the experiment is running."""
    @kernel
    def monitor_loop(self):
        j = 0
        pd_reading = [0] * 300
        self.set_dataset(
            "SUServo.Sampler.reading",
            pd_reading,
            broadcast=True,
            archive=False,
        )

        while True:
            self.suservo0.set_config(0)  # stop
            delay(20 * us)
            x = self.suservo0.get_adc(self.channel)
            delay(70 * us)
            _y = self.suservo0_ch[self.channel].get_y(0)  # profile 0
            delay(70 * us)
            s = self.suservo0.get_status()
            delay(70 * us)
            self.suservo0.set_config(1)  # restart

            # self.p1(x, y, s)  # print function

            # pz changes
            self.mutate_dataset("SUServo.Sampler.reading", j % 300, x)

            j += 1
            delay(0.05 * s)  # wait a while
            self.sch_pause()  # inturrupt check

"""The strobe() function is used to repeatedly switch the RF output of a selected SUServo channel off and on at controlled time 
intervals. It first waits for 50 million machine units using delay_mu(int(50e6)) to allow an initial delay before starting the strobing 
sequence. Inside the infinite while True loop, it disables the channel output and the IIR feedback controller using set(en_out=0, en_iir=0, profile=0), 
then waits for the specified interval tdel_mu. Next, it uses the parallel block to check whether the ARTIQ scheduler has requested a pause and, if so, exits 
the function; otherwise, it enables the output while keeping the IIR feedback controller disabled. It then waits for another interval of tdel_mu before repeating 
the cycle. Overall, this function generates a repeated on/off pattern, or strobe, on the selected RF channel, which may be useful for experiments that require controlled 
interruptions of the RF signal. Since the output is switched off during each cycle, this can affect the trapped ion, so the timing and purpose should be verified before using it in an experiment."""
    @kernel
    def strobe(self, tdel_mu):
        delay_mu(int(50e6))
        while True:
            self.suservo0_ch[self.channel].set(en_out=0, en_iir=0, profile=0)
            delay_mu(int(tdel_mu))
            with parallel:
                if self.scheduler.check_pause():
                    return
                self.suservo0_ch[self.channel].set(en_out=1, en_iir=0, profile=0)
            delay_mu(int(tdel_mu))
"""The run() function is the main execution function of the ARTIQ experiment, responsible for initializing the SUServo and Urukul hardware when required, configuring the RF output frequency, attenuation, 
amplitude, and feedback controller, and enabling the selected channel and master servo. If self.initialise is enabled, it resets the ARTIQ Core, initializes the SUServo devices, and calls set_RF() to configure
the RF system; otherwise, it resets the Core and prepares the real-time timeline without repeating the full initialization. The function then sets the attenuation register for CPLD 0, updates the selected Urukul 
output and feedback settings, and configures the RF output and feedback enable states using switch_state and feedback_on. After enabling the master servo, it saves the CPLD attenuation register value in an ARTIQ dataset 
for later reference. Finally, it calls monitor_loop() to continuously monitor the feedback signal and, if enabled, executes a frequency sweep or RF strobing sequence. One important point: because monitor_loop() contains an
infinite while True loop, the frequency_sweep() and strobe() calls that follow it will normally not execute unless monitor_loop() exits or is modified to run for a limited duration."""
    @kernel
    def run(self):
        if self.initialise:
            self.core.reset()
            delay(50 * us)
            self.suservo0.init()  # performs init of dds and cpld child-devices
            self.set_RF()

        else:
            # delay(1 * us)
            self.core.reset()
            self.core.break_realtime()

        delay(100 * us)
        self.suservo0.cplds[0].set_all_att_mu(self.AttenuationRegister)

        delay(100 * us)
        # self.set_RF()

        # atreg0 = self.suservo0.cplds[0].get_att_mu() #this is very important (i think)
        #               NO - its broken for suservo, always returns 0000 (all max atten)
        # atreg1 = self.suservo0.cplds[1].get_att_mu() #this is very important (i think)
        ## att levels must be read from hardware each experiment
        ## run since setting one channel requires knowledge of all 4,
        ## and by default would reset others to '0'.

        self.core.break_realtime()
        self.update_urukul_output()
        self.core.break_realtime()
        self.update_urukul_feedback()
        self.update_urukul_output_RF()
        
        ##channel enable
        delay(180 * us)
        self.suservo0_ch[self.channel].set(en_out=self.switch_state, en_iir=self.feedback_on, profile=0)

        ## master servo enable
        delay(180 * us)
        self.suservo0.set_config(enable=1)

        # self.core.break_realtime()
        # print(
        #     "Attenuation on CH0 (AOM) Suservo:",
        #     (255 - int32((self.suservo0.cplds[0].att_reg >> (0 * 8)) & 0xFF))
        #     / 8,
        # )
        # self.core.break_realtime()
        # print(
        #     "Attenuation on CH1 (TRAP RF) Suservo:",
        #     (255 - int32((self.suservo0.cplds[0].att_reg >> (1 * 8)) & 0xFF))
        #     / 8,
        # )
        # self.core.break_realtime()
        # print(
        #     "Attenuation on CH2 (TICKLE RADIAL) Suservo:",
        #     (255 - int32((self.suservo0.cplds[0].att_reg >> (2 * 8)) & 0xFF))
        #     / 8,
        # )
        # self.core.break_realtime()
        # print(
        #     "Attenuation on CH3 (TICKLE AXIAL) Suservo:",
        #     (255 - int32((self.suservo0.cplds[0].att_reg >> (3 * 8)) & 0xFF))
        #     / 8,
        # )

        # save registers to dataset for later use
        att_reg_after = self.suservo0.cplds[0].att_reg
        self.set_dataset(
            "suservo.att_reg",
            att_reg_after,
            broadcast=True,
            archive=False,
            persist=True,
        )

        # self.stringprint('INITIAL READINGS')
        # delay(150*ms)
        # self.statusprint(self.suservo0.get_status())

        # delay(150*ms)
        # v = self.suservo0.get_adc(self.channel)
        # self.stringprint('a single adc reading')
        # print(v)
        # delay(150*ms)1 (10^)
        # v = self.suservo0.get_adc(self.channel)
        # self.stringprint('a single adc reading')
        # print(v)
        # delay(150*ms)

        # self.stringprint('ONGOING READINGS')
        # delay(150*ms)
        self.monitor_loop()

        if self.frequency_sweep_on:
            self.frequency_sweep(self.freqs, 1e6)
        if self.strobe_on:
            self.strobe(8e7)

    # def analyze(self):
    #     self.set_dataset(
    #         "AOM.Params.PIDParams",
    #         [
    #             float(self.channel),
    #             self.prop_gain,
    #             self.intg_gain,
    #             self.intg_limit,
    #             0.0,
    #         ],
    #         archive=False,
    #         broadcast=True,
    #     )

        






