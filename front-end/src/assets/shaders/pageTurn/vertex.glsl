vec3 transformed = vec3(position);

float pageWeight = clamp(-position.y / uPageHeight, 0.0, 1.0);
float pageOffset = pageDeformOffset(position);
transformed.z += pageOffset;
transformed.x += sin(pageWeight * 3.14159265359)
  * sin(uPageTime * 5.0 + pageWeight * 4.0)
  * uPageFlutter
  * 0.16;
transformed.y -= abs(pageOffset) * pageWeight * 0.035;
