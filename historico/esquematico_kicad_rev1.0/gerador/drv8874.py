def _pin(typ, x, y, ang, name, num):
    return (f'      (pin {typ} line (at {x} {y} {ang}) (length 2.54)\n'
            f'        (name "{name}" (effects (font (size 1.27 1.27))))\n'
            f'        (number "{num}" (effects (font (size 1.27 1.27))))\n      )\n')
def drv_block():
    L=[('input','EN/IN1','1'),('input','PH/IN2','2'),('input','nSLEEP','3'),('input','VREF','5'),
       ('input','PMODE','16'),('input','IMODE','7'),('power_in','GND','15'),('power_in','PGND','9'),('passive','PAD','17')]
    R=[('power_in','VM','11'),('passive','VCP','12'),('passive','CPH','13'),('passive','CPL','14'),
       None,('output','OUT1','8'),('output','OUT2','10'),('output','IPROPI','6'),('open_collector','nFAULT','4')]
    b='  (symbol "DRV8874PWP" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)\n'
    for k,v,at,hide in [('Reference','U','-10.16 13.97 0',''),('Value','DRV8874PWP','0 -13.97 0',''),
                        ('Footprint','','0 0 0',' hide'),('Datasheet','https://www.ti.com/lit/ds/symlink/drv8874.pdf','0 0 0',' hide')]:
        b+=f'    (property "{k}" "{v}" (at {at})\n      (effects (font (size 1.27 1.27)){hide})\n    )\n'
    b+='    (symbol "DRV8874PWP_0_1"\n      (rectangle (start -10.16 12.7) (end 10.16 -12.7)\n        (stroke (width 0.254) (type default))\n        (fill (type background))\n      )\n    )\n'
    b+='    (symbol "DRV8874PWP_1_1"\n'
    for i,p in enumerate(L):
        y=10.16-2.54*i; b+=_pin(p[0],-12.7,round(y,2),0,p[1],p[2])
    for i,p in enumerate(R):
        if p is None: continue
        y=10.16-2.54*i; b+=_pin(p[0],12.7,round(y,2),180,p[1],p[2])
    b+='    )\n  )\n'
    return b
