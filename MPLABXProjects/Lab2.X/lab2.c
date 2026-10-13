//Armen and Mickey 
#include <xc.h>       // Microchip device-specific header (provides _CP0 macros)
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>   // Provides uint32_t

// Define your system frequency (Update this to match your board's oscillator setup)
#define SYS_FREQ 80000000UL 

#define PB_RELEASED() (_RF1 == 0) // when released, RF1 at logic low
#define PB_PRESSED()  (_RF1 == 1) // when pressed, RF1 at logic high, pull-down
#define sw (_RD8)                 // Switch configuration and access

void update_state(void);          // function update_state prototype

// Hardware-accurate delay using PIC32 Core Timer
void msDelay(uint32_t ms) {
    // Core timer ticks at half the system frequency (SYS_FREQ / 2)
    uint32_t target_ticks = ms * (SYS_FREQ / 2000);
    _CP0_SET_COUNT(0);
    while (_CP0_GET_COUNT() < target_ticks);
}

// State machine definitions
typedef enum {
    S1_IDLE,
    S1_PRESSED,
    S2_IDLE,
    S2_BLINKING,
    S3_IDLE,
    S3_PRESSED,
    S4_IDLE,
    S4_PRESSED,
    S4_BLINKING
} sw_state;

void update_state(void) {
    static sw_state mystate = S1_IDLE;
    static int blink_timer = 0;
    static int blink_count = 0;

    switch (mystate) {
        
        // --- STEP 1 ---
        // Turn LED OFF. On press and release, turn the LED on, go to step 2.
        case S1_IDLE: //s1 idle state
            if (PB_PRESSED()) {
                _LATE0 = 0; // Turn LED OFF upon pressing 
                mystate = S1_PRESSED; //state now goes to s1_pressed
            }
            break;
            
        case S1_PRESSED: //when s1 is pressed 
            if (PB_RELEASED()) {//if the button is released
                _LATE0 = 1; // Turn LED ON upon release
                mystate = S2_IDLE; //prceeds to sate 2 idle
            }
            break;

        // --- STEP 2 ---
        // On press, begin blinking. On release, freeze LED ON and go to step 3.
        case S2_IDLE:
            if (PB_PRESSED()) {
                blink_timer = 0;
                mystate = S2_BLINKING;
            }
            break;
            
        case S2_BLINKING:
            if (PB_RELEASED()) { // if the button is released the LED freezes
                _LATE0 = 1; // Freeze LED ON upon release
                mystate = S3_IDLE; //Then move to state 3
            } else {
                // 1 Hz blink rate: Toggle every 500ms (50 loops of 10ms)
                blink_timer++;
                if (blink_timer >= 50) {
                    _LATE0 = !_LATE0;
                    blink_timer = 0;
                }
            } 
           break;

        // --- STEP 3 ---
        // After press and release, if select input = 1, go to step 1; else next step.
        case S3_IDLE:
            if (PB_PRESSED()) {
                mystate = S3_PRESSED; //if the button is pressed the state goes to S3_pressed 
            }
            break;
            
        case S3_PRESSED:
            if (PB_RELEASED()) { // If sw=1, go back to s1_idle, else then contiune with s4
                if (sw == 1) {
                    mystate = S1_IDLE;
                } else {
                    mystate = S4_IDLE;
                }
            }
            break;

        // --- STEP 4 ---
        // Turn LED OFF on press and hold down. After release, blink 4 times, freeze ON, go to step 1.
        case S4_IDLE:
            if (PB_PRESSED()) { // if the button is pressed, turn off the led and set the state to s4_pressed
                _LATE0 = 0; // Turn LED OFF on press
                mystate = S4_PRESSED;
            }
            break;
            
        case S4_PRESSED:
            if (PB_RELEASED()) { // when pressed, set the blink timer and count to 0 and then set the state to blinking
                blink_timer = 0;
                blink_count = 0;
                mystate = S4_BLINKING;
            }
            break;
            
        case S4_BLINKING:
            blink_timer++;
            if (blink_timer >= 50) { // blinking function 
                _LATE0 = !_LATE0;   // Toggle LED
                blink_timer = 0;
                blink_count++;
                
                // 4 full blinks equals 8 state toggles
                if (blink_count >= 8) {
                    _LATE0 = 1;        // Freeze ON
                    mystate = S1_IDLE; // Loop back to Step 1
                }
            }
            break;

        default:
            mystate = S1_IDLE;
            break;
    }
}

int main    (void) {
    _TRISE0 = 0; // RE0 configured as output
    _TRISF1 = 1; // RF1 configured as input
    _TRISD8 = 1; // RD8 configured as input
    
    _LATE0 = 0;  // Initial LED state
    
    while (1) {
        update_state();
        msDelay(10); // Updated to use your accurate Core Timer function
    }
}