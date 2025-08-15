import traceback
import sys
import logging
from BOT.BOT import BOT

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

def MAIN():
    logging.info("MAIN() activated.")
    BOT()
    logging.info("MAIN() complete.")

if __name__ == "__main__":
	try:
		logging.info("main.py activated.")
		MAIN()
		logging.info("main.py complete.")
	except Exception as e:
        # Print the exception traceback
		traceback.print_exc()
        # Prompt the user to press a key to continue
		if hasattr(sys, 'ps1') or sys.stdin.isatty():
			input("Press Enter to continue...")