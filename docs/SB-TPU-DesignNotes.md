# Coral Cubed TPU Design Report

Contributors: Jack Rathert

## Hardware Subsystems

The SB-TPU is a complex pico-scale embedded system comprising of the following primary systems:

- Google Coral Edge TPU
  - An embedded ML accelerator and associated filtering circuity
  - Takes both 1V8 and 3V3 power inputs
  - Communicates with MCU (microcontroller unit) via USB (Universal Serial Bus) OTG lanes
- NXP RT1176 Microcontroller
  - Contains an ARM Cortex M4 and M7, with shared memory.
    - USB interface
    - Takes 3V3 and 1V8 power inputs, with 5V USB VRef to signal USB connections.
- Data Systems
  - NAND Flash: Micron MT29F1G01ABBFDWB-IT:F TR
    1 Gbit NAND flash, communicates with with MCU via QSPI
  - SDRAM: MT48H32M16LFB4-6 IT:C
    512 Mbit Micron SDRAM memory. This is reaching obsalecence, it is still available through some retailers and JLC directly, but not via DigiKey. Need to find a minimal firmware update replacement.
- Power Management:
  - LM3370SD-4221/NOPB Dual Synchronous Step-Down DC-DC Converter
  - POR Supervisory Circuit TPS3813K33DBVR
        I am now less certain that I need this.
  - LTC4413EDD-1_TRPBF: ORing Ideal Diode Controller
    - Allows for 3V3 Rail to not conflict with USB power off Buck 3V3 output.
- USB Controller
