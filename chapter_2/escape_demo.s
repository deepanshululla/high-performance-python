	.section	__TEXT,__text,regular,pure_instructions
	.build_version macos, 26, 0	sdk_version 26, 2
	.globl	_inc                            ; -- Begin function inc
	.p2align	2
_inc:                                   ; @inc
	.cfi_startproc
; %bb.0:
	add	w0, w0, #1
	ret
	.cfi_endproc
                                        ; -- End function
	.globl	_z_squared_plus_c               ; -- Begin function z_squared_plus_c
	.p2align	2
_z_squared_plus_c:                      ; @z_squared_plus_c
	.cfi_startproc
; %bb.0:
	ldr	d2, [x0]
	ldr	d3, [x1]
	fnmul	d4, d3, d3
	fmadd	d4, d2, d2, d4
	fadd	d0, d4, d0
	str	d0, [x0]
	fadd	d0, d2, d2
	fmadd	d0, d0, d3, d1
	str	d0, [x1]
	ret
	.cfi_endproc
                                        ; -- End function
.subsections_via_symbols
