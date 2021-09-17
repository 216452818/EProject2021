from smbus import SMBus
import re
import platform
import time

class ADCPi(object):
    """
    Control the MCP3424 ADC on the ADC Pi Plus and ADC Pi Zero
    """
    # internal variables
    __adc_address = 0x68

    __adc_conf = 0x9C

    __adc_channel = 0x01

    __bitrate = 18  # current bitrate
    __conversionmode = 1  # Conversion Mode
    __pga = float(0.5)  # current pga setting
    __lsb = float(0.0000078125)  # default lsb value for 18 bit
    __signbit = 0  # stores the sign bit for the sampled value

    # create byte array and fill with initial values to define size
    __adcreading = bytearray([0, 0, 0, 0])

    __bus = None

    # local methods

    def __updatebyte(self, byte, mask, value):
        """
        Internal method for setting the value of a single bit within a byte

        :param byte: input value
        :type byte: int
        :param mask: location to update
        :type mask: int
        :param value: new bit, 0 or 1
        :type value: int
        :return: updated value
        :rtype: int
        """
        byte &= mask
        byte |= value
        return byte

    def __setchannel(self, channel):
        """
        Internal method for updating the config to the selected channel

        :param channel: selected channel
        :type channel: int
        """
        if channel != self.__adc_channel:
            self.__adc_channel = channel
            if channel == 1:  # bit 5 = 1, bit 6 = 0
                self.__adc_conf = self.__updatebyte(self.__adc_conf,
                                                     0x9F, 0x00)
            elif channel == 2:  # bit 5 = 1, bit 6 = 0
                self.__adc_conf = self.__updatebyte(self.__adc_conf,
                                                     0x9F, 0x20)
            elif channel == 3:  # bit 5 = 0, bit 6 = 1
                self.__adc_conf = self.__updatebyte(self.__adc_conf,
                                                     0x9F, 0x40)
            elif channel == 4:  # bit 5 = 1, bit 6 = 1
                self.__adc_conf = self.__updatebyte(self.__adc_conf,
                                                     0x9F, 0x60)
        return

    # init object with i2caddress, default is 0x68, 0x69 for ADCoPi board
    def __init__(self, address=0x68, rate=18, bus=None):
        """
        Class constructor - Initialise the two ADC chips with their
        I2C addresses and bit rate.

        :param address: I2C address for channels 1 to 4, defaults to 0x68
        :type address: int, optional
        :param address2: I2C address for channels 5 to 8, defaults to 0x69
        :type address2: int, optional
        :param rate: bit rate, defaults to 18
        :type rate: int, optional
        :param bus: I2C bus number.  If no value is set the class will try to
                    find the i2c bus automatically using the device name
        :type bus: int, optional
        """
        self.__bus = self.__get_smbus(bus)
        self.__adc_address = address
        self.set_bit_rate(rate)

    def read_voltage(self, channel):
        """
        Returns the voltage from the selected ADC channel

        :param channel: 1 to 8
        :type channel: int
        :return: voltage
        :rtype: float
        """
        if channel < 1 or channel > 4:
            raise ValueError('read_voltage: channel out of range (1 to 4 allowed)')

        raw = self.read_raw(channel)
        voltage = float(0.0)
        if not self.__signbit:
            voltage = float(
                (raw * (self.__lsb / self.__pga)) * 2.471)

        return voltage

    def read_raw(self, channel):
        """
        Reads the raw value from the selected ADC channel

        :param channel: 1 to 8
        :type channel: int
        :raises ValueError: read_raw: channel out of range
        :raises TimeoutError: read_raw: channel x conversion timed out
        :return: raw ADC output
        :rtype: int
        """
        if channel < 1 or channel > 4:
            raise ValueError('read_raw: channel out of range (1 to 4 allowed)')

        high = 0
        low = 0
        mid = 0
        cmdbyte = 0

        # get the config and i2c address for the selected channel
        self.__setchannel(channel)        
        config = self.__adc_conf
        address = self.__adc_address

        # if the conversion mode is set to one-shot update the ready bit to 1
        if self.__conversionmode == 0:
            config = config | (1 << 7)
            self.__bus.write_byte(address, config)
            config = config & ~(1 << 7)  # reset the ready bit to 0

        # determine a reasonable amount of time to wait for a conversion
        if self.__bitrate == 18:
            seconds_per_sample = 0.26666
        elif self.__bitrate == 16:
            seconds_per_sample = 0.06666
        elif self.__bitrate == 14:
            seconds_per_sample = 0.01666
        elif self.__bitrate == 12:
            seconds_per_sample = 0.00416
        timeout_time = time.time() + (100 * seconds_per_sample)

        # keep reading the adc data until the conversion result is ready
        while True:
            __adcreading = self.__bus.read_i2c_block_data(address, config, 4)
            if self.__bitrate == 18:
                high = __adcreading[0]
                mid = __adcreading[1]
                low = __adcreading[2]
                cmdbyte = __adcreading[3]
            else:
                high = __adcreading[0]
                mid = __adcreading[1]
                cmdbyte = __adcreading[2]
            # check if bit 7 of the command byte is 0.
            if(cmdbyte & (1 << 7)) == 0:
                break
            elif time.time() > timeout_time:
                msg = 'read_raw: channel %i conversion timed out' % channel
                raise TimeoutError(msg)
            else:
                time.sleep(0.00001)  # sleep for 10 microseconds

        self.__signbit = False
        raw = 0
        # extract the returned bytes and combine in the correct order
        if self.__bitrate == 18:
            raw = ((high & 0x03) << 16) | (mid << 8) | low
            self.__signbit = bool(raw & (1 << 17))
            raw = raw & ~(1 << 17)  # reset sign bit to 0

        elif self.__bitrate == 16:
            raw = (high << 8) | mid
            self.__signbit = bool(raw & (1 << 15))
            raw = raw & ~(1 << 15)  # reset sign bit to 0

        elif self.__bitrate == 14:
            raw = ((high & 0b00111111) << 8) | mid
            self.__signbit = bool(raw & (1 << 13))
            raw = raw & ~(1 << 13)  # reset sign bit to 0

        elif self.__bitrate == 12:
            raw = ((high & 0x0f) << 8) | mid
            self.__signbit = bool(raw & (1 << 11))
            raw = raw & ~(1 << 11)  # reset sign bit to 0

        return raw

    def set_pga(self, gain):
        """
        PGA (programmable gain amplifier) gain selection

        :param gain: 1 = 1x
                     2 = 2x
                     4 = 4x
                     8 = 8x
        :type gain: int
        :raises ValueError: set_pga: gain out of range
        """

        if gain == 1:
            # bit 0 = 0, bit 1 = 0
            self.__adc_conf = self.__updatebyte(self.__adc_conf, 0xFC, 0x00)
            self.__pga = 0.5
        elif gain == 2:
            # bit 0 = 1, bit 1 = 0
            self.__adc_conf = self.__updatebyte(self.__adc_conf, 0xFC, 0x01)
            self.__pga = 1.0
        elif gain == 4:
            # bit 0 = 0, bit 1 = 1
            self.__adc_conf = self.__updatebyte(self.__adc_conf, 0xFC, 0x02)
            self.__pga = 2.0
        elif gain == 8:
            # bit 0 = 1, bit 1 = 1
            self.__adc_conf = self.__updatebyte(self.__adc_conf, 0xFC, 0x03)
            self.__pga = 4.0
        else:
            raise ValueError('set_pga: gain out of range')

        self.__bus.write_byte(self.__adc_address, self.__adc_conf)
        return

    def set_bit_rate(self, rate):
        """
        Sample rate and resolution

        :param rate: 12 = 12 bit (240SPS max)
                     14 = 14 bit (60SPS max)
                     16 = 16 bit (15SPS max)
                     18 = 18 bit (3.75SPS max)
        :type rate: int
        :raises ValueError: set_bit_rate: rate out of range
        """

        if rate == 12:
            # bit 2 = 0, bit 3 = 0
            self.__adc_conf = self.__updatebyte(self.__adc_conf, 0xF3, 0x00)
            self.__bitrate = 12
            self.__lsb = 0.0005
        elif rate == 14:
            # bit 2 = 1, bit 3 = 0
            self.__adc_conf = self.__updatebyte(self.__adc_conf, 0xF3, 0x04)
            self.__bitrate = 14
            self.__lsb = 0.000125
        elif rate == 16:
            # bit 2 = 0, bit 3 = 1
            self.__adc_conf = self.__updatebyte(self.__adc_conf, 0xF3, 0x08)
            self.__bitrate = 16
            self.__lsb = 0.00003125
        elif rate == 18:
            # bit 2 = 1, bit 3 = 1
            self.__adc_conf = self.__updatebyte(self.__adc_conf, 0xF3, 0x0C)
            self.__bitrate = 18
            self.__lsb = 0.0000078125
        else:
            raise ValueError('set_bit_rate: rate out of range')

        self.__bus.write_byte(self.__adc_address, self.__adc_conf)
        return

    def set_conversion_mode(self, mode):
        """
        conversion mode for adc

        :param mode: 0 = One shot conversion mode
                     1 = Continuous conversion mode
        :type mode: int
        :raises ValueError: set_conversion_mode: mode out of range
        """
        if mode == 0:
            # bit 4 = 0
            self.__adc_conf = self.__updatebyte(self.__adc_conf, 0xEF, 0x00)
            self.__conversionmode = 0
        elif mode == 1:
            # bit 4 = 1
            self.__adc_conf = self.__updatebyte(self.__adc_conf, 0xEF, 0x10)
            self.__conversionmode = 1
        else:
            raise ValueError('set_conversion_mode: mode out of range')

        return
