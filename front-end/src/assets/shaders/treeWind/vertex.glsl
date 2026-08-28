vec3 transformed = vec3(position);

float normalizedHeight = clamp(
  (position.z - uWindMinZ) / uWindHeight,
  0.0,
  1.0
);
float crownWeight = pow(smoothstep(0.12, 0.72, normalizedHeight), 1.7);
float mainWind = sin(uWindTime * 1.15 + uWindPhase);
float softGust = sin(
  uWindTime * 0.31 + uWindPhase * 1.7 + position.z * 0.42
) * 0.32;
float bend = (mainWind + softGust) * uWindStrength * crownWeight;

transformed.x += bend;
transformed.y += cos(uWindTime * 0.67 + uWindPhase)
  * uWindStrength
  * 0.28
  * crownWeight;
