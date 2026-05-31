# Satellite network generation with satgenpy

Python framework to define LEO constellations, ground stations, ISL topology, and
time-varying forwarding state for analysis and ns-3 simulation.

It produces:

* `ground_stations.txt` : Ground station locations and metadata
* `tles.txt` : Satellite orbits (TLE / SGP-4)
* `isls.txt` : Inter-satellite link topology
* `gsl_interfaces_info.txt` : GSL interface counts and bandwidth per node
* `description.txt` : Max GSL / ISL reach in meters
* `dynamic_state/` : Per-timestep `fstate_*.txt` and `gsl_if_bandwidth_*.txt`

Located at: `satgenpy/`

## Getting started

1. Python 3.7+ on Linux.

2. Install dependencies:
   ```
   pip install numpy astropy ephem networkx sgp4 geopy matplotlib statsmodels
   sudo apt-get install libproj-dev proj-data proj-bin libgeos-dev
   pip install cartopy
   pip install git+https://github.com/snkas/exputilpy.git@v1.6
   ```

3. Use the generators under `satgenpy/satgen/` from `paper/satellite_networks_state/`
   (see `paper/satellite_networks_state/README.md`) or call the APIs from your own scripts.

## Dynamic state algorithms

* `algorithm_free_one_only_over_isls` : Shortest paths over ISLs only; one GSL interface per node; GS-(SAT)+-GS paths.

* `algorithm_free_one_only_gs_relays` : No ISLs; ground-station relay paths GS-SAT-(GS-SAT)+-GS.

* `algorithm_free_gs_one_sat_many_only_over_isls` : ISLs; one GSL interface per ground station, many per satellite (per-destination satellite interfaces).

* `algorithm_paired_many_over_isls` : ISLs; paired GSL interfaces with bandwidth sharing (early development).

## File formats

### Ground stations

Comma-separated file describing ground stations.

**Line format (basic): `ground_stations.basic.txt`**

```
[id: int],[name: string],[latitude: float],[longitude: float],[elevation: float]
```

**Example:**

```
0,City: Tokyo; Country: Japan,35.6895,139.69171,0.0
1,City: Delhi; Country: India,28.66667,77.21667,0.0
```

**Line format (extended): `ground_stations.txt`**

```
[id: int],[name: string],[latitude: float],[longitude: float],[elevation: float],[x cartesian: float],[y cartesian: float],[z cartesian: float]
```

**Notes:** IDs increment by 1; ground-station **node** IDs follow all satellites (e.g. 625 satellites → first GS node id 625).

### Satellite orbits: `tles.txt`

First line: `[num_orbits] [sats_per_orbit]`. Each satellite uses a four-line TLE block (see NASA TLE definition). Satellite ids follow file order from 0.

**Example:**

```
1 1
Starlink 0
1 00001U 19029BR  18161.59692852  .00001103  00000-0  33518-4 0  9994
2 00001 53.00000   0.7036 0003481 299.7327   0.3331 15.05527065  1773
```

### Satellite topology: `isls.txt`

One ISL per line: `[from_sat_id] [to_sat_id]`

**Example:**

```
0 1
0 2
1 2
```

### GSL interfaces: `gsl_interfaces_info.txt`

```
[node id],[number of GSL interfaces],[max. aggregate bandwidth]
```

**Example:** `329,5,2.0` — node 329 has 5 interfaces, aggregate cap 2.0.

### Description: `description.txt`

```
max_gsl_length_m=<float>
max_isl_length_m=<float>
```

### Forwarding state: `dynamic_state/fstate_<time_ns>.txt`

```
[current],[dest],[next-hop],[current-interface-id],[next-hop-interface-id]
```

**Example:** `301,992,340,3,5` — at node 301, traffic for 992 goes to 340 via interfaces 3→5.

Only routes **to ground stations** are stored (satellites are not destinations).

### GSL bandwidth: `dynamic_state/gsl_if_bandwidth_<time_ns>.txt`

```
[node],[interface-id],[bandwidth (unitless)]
```

**Example:** `145,1,0.4`
