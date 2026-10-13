//Armen and mickey
#include <p32xxxx.h>
#define C1  PORTAbits.RA9
#define C2  PORTAbits.RA10
#define C3  PORTAbits.RA14
#define C4  PORTAbits.RA15

#define NO_KEY  -1

int  ReadTopRow(void);          // returns 1, 2, 3, 10 (A) or NO_KEY
void msDelay(unsigned msec);

// Value assigned to each key of the top row (columns C1..C4)
const int topRowKeys[4] = {1, 2, 3, 10};

void main(void)
{
    int keyNum;

    DDPCONbits.JTAGEN = 0;   // Disable JTAG (RA4/RA5 are shared with JTAG TDI/TDO)

    TRISA = 0xC600;          // RA15, RA14, RA10, RA9 = inputs; RA7-RA4 = outputs
    TRISF = 0;               // PORTF = outputs (LEDs)
    LATF  = 0;               // LEDs off

    while (1)
    {
        keyNum = ReadTopRow();

        if (keyNum != NO_KEY)
            LATF = keyNum & 0x0F;   // show binary value on RF0-RF3
        else
            LATF = 0;               // no key from top row -> LEDs off

        msDelay(20);                // delay between scans (also debounces)
    }
}

int ReadTopRow(void)
{
    LATACLR = 0x0010;        // RA4 (Row 1) = 0
    LATASET = 0x00E0;        // RA5, RA6, RA7 (Rows 2-4) = 1
    msDelay(2);              // let the output pins settle

    if      (C1 == 0) return topRowKeys[0];   // key 1
    else if (C2 == 0) return topRowKeys[1];   // key 2
    else if (C3 == 0) return topRowKeys[2];   // key 3
    else if (C4 == 0) return topRowKeys[3];   // key A = 10 (binary 1010)
    else              return NO_KEY;
}

void msDelay(unsigned msec)
{
    volatile unsigned i, j;
    for (i = 0; i < msec; i++)
        for (j = 0; j < 1000; j++)
            ;
}
