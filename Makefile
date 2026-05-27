ARDUINO_CLI ?= arduino-cli
TEENSY_FQBN ?= teensy:avr:teensy41
TEENSY_SKETCH ?= teensy_controller
TEENSY_BUILD_PATH ?= /private/tmp/space-io-arduino-build
TEENSY_PORT ?=

.PHONY: teensy-compile teensy-upload teensy-board-list

teensy-compile:
	$(ARDUINO_CLI) compile --fqbn $(TEENSY_FQBN) --build-path $(TEENSY_BUILD_PATH) $(TEENSY_SKETCH)

teensy-upload: teensy-compile
	$(if $(TEENSY_PORT),,$(error Set TEENSY_PORT=usb:... from make teensy-board-list))
	$(ARDUINO_CLI) upload --fqbn $(TEENSY_FQBN) --build-path $(TEENSY_BUILD_PATH) --port $(TEENSY_PORT) $(TEENSY_SKETCH)

teensy-board-list:
	$(ARDUINO_CLI) board list
