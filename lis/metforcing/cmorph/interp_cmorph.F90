!-----------------------BEGIN NOTICE -- DO NOT EDIT-----------------------
! NASA Goddard Space Flight Center
! Land Information System Framework (LISF)
! Version 7.5
!
! Copyright (c) 2024 United States Government as represented by the
! Administrator of the National Aeronautics and Space Administration.
! All Rights Reserved.
!-------------------------END NOTICE -- DO NOT EDIT-----------------------
!BOP
!
! !ROUTINE: interp_cmorph
! \label{interp_cmorph}
!
!
! !INTERFACE: 
subroutine interp_cmorph(n, nx, ny, finput, lis_gds, nc, nr, varfield)
! !USES:
  use LIS_coreMod,       only : LIS_domain
  use cmorph_forcingMod, only : cmorph_struc

  implicit none
! !ARGUMENTS: 
  integer, intent(in) :: n 
  integer             :: nx
  integer             :: ny
  integer             :: nc
  integer             :: nr
  real, dimension(nx,ny) :: finput
  real, dimension(nc,nr) :: varfield
!
! !DESCRIPTION:
!   This subroutine interpolates a given CMORPH field 
!   to the LIS grid. 
!  The arguments are: 
!  \begin{description}
! \item[n]
!  index of the nest
! \item[nx]
!  number of columns (in the east-west dimension) in the CMORPH grid
! \item[ny]
!  number of rows (in the north-south dimension) in the CMORPH grid
! \item[finput]
!  input data array to be interpolated
! \item[lis\_gds]
!  array description of the LIS grid
! \item[nc]
!  number of columns (in the east-west dimension) in the LIS grid
! \item[nr]
!  number of rows (in the north-south dimension) in the LIS grid
! \item[varfield]
!  output interpolated field
!  \end{description} 
! 
!
!  The routines invoked are: 
!  \begin{description}
!  \item[conserv\_interp](\ref{conserv_interp}) \newline
!    spatially interpolate the forcing data using conservative interpolation
! \end{description}
!EOP
  real :: lis_gds(50)
  logical*1, dimension(nx*ny)  :: lb
  logical*1, dimension(nc*nr)  :: lo
  real, dimension(nx*ny) :: f
  integer             :: ngdas

  integer :: iret
  integer :: mo
  integer :: count1,i,j,v
  real, dimension(nc*nr) :: lis1d

!=== End variable declarations

!--------------------------------------------------------------------
! Setting interpolation options (ip=0,bilinear)
! (km=1, one parameter, ibi=1,use undefined bitmap
! (needed for soil moisture and temperature only)
! Use budget bilinear (ip=3) for precip forcing fields
!--------------------------------------------------------------------
  ngdas = nx * ny
  mo = nc*nr

  v = 0
  Do j=1, ny
     Do i=1, nx
        v = v+ 1
        f(v) = finput(i, j)
     End Do
  End Do
  
!--------------------------------------------------------------------
! Initialize output bitmap. Important for soil moisture and temp.
!--------------------------------------------------------------------
  lb = .true.
  lo = .true.


  cmorph_struc(n)%mi = ngdas

  call conserv_interp(lis_gds,lb,f,lo,lis1d,cmorph_struc(n)%mi,mo,&
       LIS_domain(n)%lat, LIS_domain(n)%lon,cmorph_struc(n)%w112,&
       cmorph_struc(n)%w122,cmorph_struc(n)%w212,cmorph_struc(n)%w222,&
       cmorph_struc(n)%n112,cmorph_struc(n)%n122,cmorph_struc(n)%n212,&
       cmorph_struc(n)%n222,-9999.0, iret)

!--------------------------------------------------------------------
! Create 2D array for main program. Also define a "soil" mask
! due to different geography between GDAS & LDAS. For LDAS land
! points not included in GDAS geography dataset only.
!--------------------------------------------------------------------
  count1 = 0
  do j = 1, nr
     do i = 1, nc
        varfield(i,j) = lis1d(i+count1)
     enddo
     count1 = count1 + nc
  enddo

end subroutine interp_cmorph

