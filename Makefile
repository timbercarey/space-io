ARDUINO_CLI ?= arduino-cli
TEENSY_FQBN ?= teensy:avr:teensy41
TEENSY_SKETCH ?= teensy_controller/teensy_controller.ino
TEENSY_BUILD_PATH ?= /private/tmp/space-io-arduino-build
TEENSY_PORT ?=
HAPKIT_FQBN ?= arduino:avr:uno
HAPKIT_ERM_SKETCH ?= hapkit_erm_controller
HAPKIT_ERM_BUILD_PATH ?= /private/tmp/space-io-hapkit-erm-build
HAPKIT_PORT ?=

.PHONY: teensy-compile teensy-upload teensy-board-list hapkit-erm-compile hapkit-erm-upload

teensy-compile:
	$(ARDUINO_CLI) compile --clean --fqbn $(TEENSY_FQBN) --build-path $(TEENSY_BUILD_PATH) $(TEENSY_SKETCH)

teensy-upload: teensy-compile
	$(if $(TEENSY_PORT),,$(error Set TEENSY_PORT=usb:... from make teensy-board-list))
	$(ARDUINO_CLI) upload --fqbn $(TEENSY_FQBN) --build-path $(TEENSY_BUILD_PATH) --port $(TEENSY_PORT) $(TEENSY_SKETCH)

teensy-board-list:
	$(ARDUINO_CLI) board list

hapkit-erm-compile:
	$(ARDUINO_CLI) compile --clean --fqbn $(HAPKIT_FQBN) --build-path $(HAPKIT_ERM_BUILD_PATH) $(HAPKIT_ERM_SKETCH)

hapkit-erm-upload: hapkit-erm-compile
	$(if $(HAPKIT_PORT),,$(error Set HAPKIT_PORT from arduino-cli board list))
	$(ARDUINO_CLI) upload --fqbn $(HAPKIT_FQBN) --build-path $(HAPKIT_ERM_BUILD_PATH) --port $(HAPKIT_PORT) $(HAPKIT_ERM_SKETCH)
