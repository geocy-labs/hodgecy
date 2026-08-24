# HodgeCY II Baseline - 239 / 240 / 241

## local_inventory
State: equal
- `{"l3":0,"p3":16,"p4_0":10,"p4_1":0,"p5_0":0,"p5_1":0,"p5_2":0}`: hodgecy-ii-239, hodgecy-ii-240, hodgecy-ii-241

## matrix_shape
State: equal
- `[26,28]`: hodgecy-ii-239, hodgecy-ii-240, hodgecy-ii-241

## rank_Q
State: different
- `24`: hodgecy-ii-241
- `26`: hodgecy-ii-239, hodgecy-ii-240

## rank_mod_2
State: different
- `21`: hodgecy-ii-239
- `23`: hodgecy-ii-240
- `24`: hodgecy-ii-241

## rank_mod_3
State: different
- `19`: hodgecy-ii-241
- `24`: hodgecy-ii-240
- `25`: hodgecy-ii-239

## kernel_dim_Q
State: different
- `2`: hodgecy-ii-239, hodgecy-ii-240
- `4`: hodgecy-ii-241

## cokernel_dim_Q
State: different
- `0`: hodgecy-ii-239, hodgecy-ii-240
- `2`: hodgecy-ii-241

## integral_kernel_rank
State: different
- `2`: hodgecy-ii-239, hodgecy-ii-240
- `4`: hodgecy-ii-241

## integral_cokernel_decomposition
State: different
- `{"canonical":"Z/2Z + (Z/4Z)^3 + Z/12Z","free_rank":0,"torsion_factors":[2,4,4,4,12]}`: hodgecy-ii-239
- `{"canonical":"Z/2Z + Z/6Z + Z/12Z","free_rank":0,"torsion_factors":[2,6,12]}`: hodgecy-ii-240
- `{"canonical":"Z^2 + (Z/3Z)^5","free_rank":2,"torsion_factors":[3,3,3,3,3]}`: hodgecy-ii-241

## smith_normal_form
State: different
- `[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,6,12]`: hodgecy-ii-240
- `[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,4,4,4,12]`: hodgecy-ii-239
- `[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,3,3,3,3,3]`: hodgecy-ii-241

## automorphism_group_order
State: different
- `24`: hodgecy-ii-239
- `32`: hodgecy-ii-241
- `6`: hodgecy-ii-240

## plane_orbit_sizes
State: different
- `[1,1,3,3]`: hodgecy-ii-240
- `[4,4]`: hodgecy-ii-239
- `[8]`: hodgecy-ii-241

## double_line_orbit_sizes
State: different
- `[1,3,3,3,3,3,3,3,6]`: hodgecy-ii-240
- `[4,6,6,12]`: hodgecy-ii-239
- `[4,8,16]`: hodgecy-ii-241

## multiple_point_orbit_sizes
State: different
- `[1,1,3,3,3,3,3,3,6]`: hodgecy-ii-240
- `[2,8,16]`: hodgecy-ii-241
- `[4,4,6,12]`: hodgecy-ii-239

## character_C1_distribution
State: different
- `{"0":16,"28":1,"4":13,"8":2}`: hodgecy-ii-241
- `{"0":6,"1":8,"28":1,"4":3,"8":6}`: hodgecy-ii-239
- `{"1":2,"28":1,"8":3}`: hodgecy-ii-240

## character_C0_distribution
State: different
- `{"0":16,"2":5,"26":1,"4":4,"6":2,"8":4}`: hodgecy-ii-241
- `{"0":6,"2":11,"26":1,"8":6}`: hodgecy-ii-239
- `{"2":2,"26":1,"8":3}`: hodgecy-ii-240

# Refinement

## Level 0: local_inventory
- hodgecy-ii-239, hodgecy-ii-240, hodgecy-ii-241

## Level 1: local_inventory, rank_Q, kernel_dim_Q, cokernel_dim_Q
- hodgecy-ii-239, hodgecy-ii-240
- hodgecy-ii-241

## Level 2: local_inventory, rank_Q, kernel_dim_Q, cokernel_dim_Q, smith_normal_form, integral_cokernel_decomposition
- hodgecy-ii-239
- hodgecy-ii-240
- hodgecy-ii-241

## Level 3: local_inventory, rank_Q, kernel_dim_Q, cokernel_dim_Q, smith_normal_form, integral_cokernel_decomposition, automorphism_group_order, plane_orbit_sizes, double_line_orbit_sizes, multiple_point_orbit_sizes
- hodgecy-ii-239
- hodgecy-ii-241
- hodgecy-ii-240

## Level 4: local_inventory, rank_Q, kernel_dim_Q, cokernel_dim_Q, smith_normal_form, integral_cokernel_decomposition, automorphism_group_order, plane_orbit_sizes, double_line_orbit_sizes, multiple_point_orbit_sizes, character_C1_distribution, character_C0_distribution
- hodgecy-ii-239
- hodgecy-ii-241
- hodgecy-ii-240

First split: rank_Q
