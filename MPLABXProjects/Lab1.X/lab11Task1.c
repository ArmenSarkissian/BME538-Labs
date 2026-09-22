//Armen and mickey 
#include <p32xxxx.h>
#include <xc.h>
#include <stdint.h>

void msDelay(uint32_t count) {
    volatile uint32_t i;
    for (i = 0; i < count * 1000; i++) {
        Nop();
    }
}
uint32_t bitmap[5]={
    0xf44f, // H 
    0x0fdd, // E
    0x0f11, //L
    0x0f11, //L
    0xf99f //O
};
int main(void){
    TRISD=0x0000;

    while (1){
        for(int i =0; i<5; i++){
            LATD = bitmap[i];
            msDelay (1000);            
            LATD=0x0000;
            msDelay(100);
            
        }
   
    }
    return 0;
}