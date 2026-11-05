#include <xc.h>
#include <sys/attribs.h>
#pragma config FNOSC    = FRCPLL
#pragma config FCKSM    = CSDCMD
#pragma config FPLLIDIV = DIV_2
#pragma config FPLLMUL  = MUL_16
#pragma config FPLLODIV = DIV_16
#pragma config FPBDIV   = DIV_2

#define PR2_VALUE 39999   // 50 Hz PWM (2 MHz / 50 - 1)

volatile int duty = 0;


//Timer 3 Interrupt
void __ISR(_TIMER_3_VECTOR, IPL3SOFT) Timer3Handler(void)
{
    IFS0bits.T3IF = 0;   // Clear interrupt flag

    if (duty < 100)
    {
        duty++;
        OC3RS = (PR2_VALUE + 1) * duty / 100;
    }
    else
    {
        duty = 0;        // Restart ramp
        OC3RS = 0;
    }
}

int main (void){
    DDPCONbits.JTAGEN = 0;

    TRISDbits.TRISD2 = 0;
    LATDbits.LATD2 = 0;
    
    // Timer 2 - PWM at 50 Hz
    T2CON = 0;
    TMR2 = 0;
    PR2 = PR2_VALUE;

    // OC3 PWM
    OC3CON = 0;
    OC3R = 0;
    OC3RS = 0;
    OC3CONbits.OCTSEL = 0;
    OC3CONbits.OCM = 0b110;

    // Timer 3 - Interrupt every 70 ms
    T3CON = 0;
    T3CONbits.TCKPS = 0b011;  // 1:8 prescaler
    TMR3 = 0;
    PR3 = 17499;              // 70 ms

    IPC3bits.T3IP = 3;
    IPC3bits.T3IS = 0;
    IFS0bits.T3IF = 0;
    IEC0bits.T3IE = 1;

    INTCONbits.MVEC = 1;
    
        __builtin_enable_interrupts();

    T2CONbits.ON = 1;
    OC3CONbits.ON = 1;
    T3CONbits.ON = 1;

    while (1)
    {
    }

    return 0;
}

    
    
    
    
}

