// -------------------------------------------------------------------------------------------------
// Pin map personnalisé pour ESP32 avec drivers stepper EN/STEP/DIR
#pragma once

#if defined(ESP32)

// Serial0: RX Pin GPIO3, TX Pin GPIO1 (to USB serial adapter)
// Serial1: RX1 Pin GPIO10, TX1 Pin GPIO9 (on SPI Flash pins, must be moved to be used)
// Serial2: RX2 Pin GPIO16, TX2 Pin GPIO17

#if SERIAL_A_BAUD_DEFAULT != OFF
  #define SERIAL_A              Serial
#endif
#if SERIAL_B_BAUD_DEFAULT != OFF
  #define SERIAL_B              Serial2
#endif

// Utilise I2C par défaut ESP32 GPIO21 (SDA) et GPIO22 (SCL)

// Les pins multi-usages (Aux3..Aux8 peuvent être analog pwm/dac si supporté)
#define AUX2_PIN                4                // ESP8266 RST control, etc.
#define AUX3_PIN                21               // I2C SDA (réservé)
#define AUX4_PIN                22               // I2C SCL (réservé)
#define AUX7_PIN                39               // Limit SW, PPS, etc. [input only 39]
#define AUX8_PIN                25               // 1-Wire, Status LED, Reticle LED, Tone, etc.

// Pins diverses
#ifndef ONE_WIRE_PIN
  #define ONE_WIRE_PIN          AUX8_PIN         // Default Pin for OneWire bus
#endif
#define ADDON_GPIO0_PIN         26               // ESP8266 GPIO0 (Dir2)
#ifndef ADDON_RESET_PIN
  #define ADDON_RESET_PIN       AUX2_PIN         // ESP8266 RST
#endif

// Le PEC index sense est une entrée logique, remet à zéro l'index PEC en rising edge puis attend 60 secondes avant de permettre un autre reset
#ifndef PEC_SENSE_PIN
  #define PEC_SENSE_PIN         36               // [input only 36] PEC Sense, analog (A0) or digital (GPIO36)
#endif

// La LED de statut est une jonction à 2 fils avec une résistance de 2k en série pour limiter le courant à la LED
#ifndef STATUS_LED_PIN
  #define STATUS_LED_PIN        AUX8_PIN         // Default LED Cathode (-)
#endif
#define MOUNT_LED_PIN           STATUS_LED_PIN   // Default LED Cathode (-)
#ifndef RETICLE_LED_PIN 
  #define RETICLE_LED_PIN       STATUS_LED_PIN   // Default LED Cathode (-)
#endif

// Pour un buzzer piezo
#ifndef STATUS_BUZZER_PIN
  #define STATUS_BUZZER_PIN     AUX8_PIN         // Tone
#endif

// La pin PPS est une entrée logique 3.3V, OnStep mesure le temps entre rising edges et ajuste la fréquence de l'horloge sidérale interne
#ifndef PPS_SENSE_PIN
  #define PPS_SENSE_PIN         AUX7_PIN         // PPS time source, GPS for example
#endif

// Le sense du limit switch est une entrée logique normalement pull high (résistance 2k), court-circuitée à ground arrête les gotos/tracking
#ifndef LIMIT_SENSE_PIN
  #define LIMIT_SENSE_PIN       AUX7_PIN
#endif

// Pins ENABLE partagées
// Non utilisé ici : AXIS1/AXIS2 ont des pins ENABLE séparées.
#define SHARED_ENABLE_PIN       OFF

// Axis1 RA/Azm stepper driver avec EN/STEP/DIR
#define AXIS1_ENABLE_PIN        13               // ENABLE pour Axis1
#define AXIS1_STEP_PIN          18               // STEP pour Axis1
#define AXIS1_DIR_PIN           19               // DIR pour Axis1
#ifndef AXIS1_SENSE_HOME_PIN
  #define AXIS1_SENSE_HOME_PIN  34               // [input only 34] Home switch Axis1
#endif

// Axis2 Dec/Alt stepper driver avec EN/STEP/DIR
#define AXIS2_ENABLE_PIN        14               // ENABLE pour Axis2
#define AXIS2_STEP_PIN          27               // STEP pour Axis2 (évite conflit avec I2C SCL)
#define AXIS2_DIR_PIN           23               // DIR pour Axis2
#ifndef AXIS2_SENSE_HOME_PIN
  #define AXIS2_SENSE_HOME_PIN  35               // [input only 35] Home switch Axis2
#endif

// Axes additionnels non utilisés (désactivés pour éviter les conflits de pins)
#define AXIS3_ENABLE_PIN        OFF
#define AXIS3_STEP_PIN          OFF
#define AXIS3_DIR_PIN           OFF

// Pour focuser1 stepper driver
#define AXIS4_ENABLE_PIN        OFF
#define AXIS4_STEP_PIN          OFF
#define AXIS4_DIR_PIN           OFF

// Pour focuser2 stepper driver
#define AXIS5_ENABLE_PIN        OFF
#define AXIS5_STEP_PIN          OFF
#define AXIS5_DIR_PIN           OFF

// ST4 interface (désactivée ici; pins 34/35 réservées pour les home switches)
#define ST4_RA_W_PIN            OFF
#define ST4_DEC_S_PIN           OFF
#define ST4_DEC_N_PIN           OFF
#define ST4_RA_E_PIN            OFF

#else
#error "Wrong processor for this configuration!"

#endif