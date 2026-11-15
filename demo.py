from spraywait import decide, single_station_decision
from spraywait.weather import SimulatedSource
from spraywait.pesticides import LocalPesticideDB

reading = SimulatedSource("evening_inversion").get_reading()
pesticide = LocalPesticideDB().get("Captan")

print("Reading at", reading.timestamp.strftime("%H:%M"))
for lv in reading.sorted_levels():
    print(f"  {lv.height_ft:>3g} ft: {lv.temp_f}F, {lv.wind_mph} mph from {lv.wind_dir_deg} deg")

g = single_station_decision(reading, pesticide)
print("\nGround station only:", g.status.value)
for r in g.reasons:
    print("  -", r)

d = decide(reading, pesticide)
print("\nSpray or Wait?:", d.status.value)
for r in d.reasons:
    print("  -", r)
