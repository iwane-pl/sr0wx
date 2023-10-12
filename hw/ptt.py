from colorama import Fore, Style
import serial
import logging

logger = logging.getLogger(__name__)


class PTT:
    def __init__(self, port, baud_rate, ptt_signal, test_mode):
        self.test_mode = test_mode
        self.ptt_signal = ptt_signal
        self.ser = None
        if self.test_mode:
            logger.info("Test mode enabled, skipping serial port usage")
        else:
            try:
                self.ser = serial.Serial(port, baud_rate)
            except serial.SerialException:
                # sudo gpasswd --add ${USER} dialout
                log = f"{Fore.RED}Failed to open serial port %s@%i\n{Style.RESET_ALL}"
                logger.error(log, port, baud_rate)

    def press(self):
        if self.ser:
            if self.ptt_signal == 'DTR':
                logger.info(f"{Fore.GREEN}DTR/PTT set to ON\n{Style.RESET_ALL}")
                self.ser.dtr = True
                self.ser.rts = False
            else:
                logger.info(f"{Fore.GREEN}RTS/PTT set to ON\n{Style.RESET_ALL}")
                self.ser.dtr = False
                self.ser.rts = True

    def release(self):
        # If we've opened serial it's now time to close it.
        if self.ser:
            self.ser.close()
            logger.info(f"{Fore.GREEN}RTS/PTT set to OFF\n{Style.RESET_ALL}")
