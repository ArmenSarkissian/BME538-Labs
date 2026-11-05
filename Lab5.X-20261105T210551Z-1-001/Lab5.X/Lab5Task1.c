#include <xc.h>

// Configuration Bits
#pragma config FNOSC    = FRCPLL
#define FCY 8000000
#pragma config FCKSM    = CSDCMD
#pragma config FPLLIDIV = DIV_2     // 4 MHz SYSCLK
#pragma config FPLLMUL  = MUL_16
#pragma config FPLLODIV = DIV_16
#pragma config FPBDIV   = DIV_2     // 2 MHz PBCLK
#define PR2_VALUE    6666           // 300 Hz PWM frequency (2 MHz / 300 - 1)
#define DUTY_VALUE   0.25*6666           // 55% Duty Cycle (0.55 * 6667)

int main(void)
{
    DDPCONbits.JTAGEN = 0;

    TRISDbits.TRISD2 = 0;
    LATDbits.LATD2   = 0;
    
    T2CON  = 0;
    OC3CON = 0;
    TMR2   = 0;
    
    PR2   = PR2_VALUE;
    OC3R  = DUTY_VALUE;             // Primary compare register (initial duty cycle)
    OC3RS = DUTY_VALUE;   
    
    OC3CONbits.OCTSEL = 0;          // 0 = Timer 2, 1 = Timer 3
    OC3CONbits.OCM    = 0b110;      // 0b110 = PWM mode
    
  
    T2CONbits.ON  = 1;              // Start Timer 2
    OC3CONbits.ON = 1;              // Enable Output Compare 3 module

    while (1)
    {
    }

    return 0;
}