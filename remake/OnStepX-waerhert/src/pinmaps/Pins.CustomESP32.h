// Pins.CustomESP32.h - Pinout personnalisé pour ESP32 WROOM
// Axes: RA, DEC | Drivers: EN, DIR, STEP | Homing | GPS Neo-6M

#ifndef PINS_CUSTOM_ESP32_H
#define PINS_CUSTOM_ESP32_H



// RA Axis
#define RA_EN_PIN      2    // Enable
#define RA_DIR_PIN     4    // Direction
#define RA_STEP_PIN    16   // Step
#define RA_HOME_PIN    17   // Homing sensor

// DEC Axis
#define DEC_EN_PIN     5
#define DEC_DIR_PIN    18
#define DEC_STEP_PIN   19
#define DEC_HOME_PIN   21   // Homing sensor

// GPS Neo-6M (UART)
#define GPS_RX_PIN     22   // ESP32 RX (connect to GPS TX)
#define GPS_TX_PIN     23   // ESP32 TX (connect to GPS RX)

// USB Serial: natif sur ESP32 (Serial)
// Pas besoin de définir, utiliser Serial ou Serial0

#endif // PINS_CUSTOM_ESP32_H
