ENTRY(rr3_apply_save)
SECTIONS {
  . = 0;
  .text : { *(.text*) }
  .rodata : { *(.rodata*) }
  /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) *(.llvm_addrsig) }
}
