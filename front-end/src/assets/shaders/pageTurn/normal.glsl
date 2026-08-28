vec3 objectNormal = vec3(normal);

float pageNormalStepX = max(uPageWidth / 192.0, 0.0001);
float pageNormalStepY = max(uPageHeight / 192.0, 0.0001);
float pageOffsetLeft = pageDeformOffset(position - vec3(pageNormalStepX, 0.0, 0.0));
float pageOffsetRight = pageDeformOffset(position + vec3(pageNormalStepX, 0.0, 0.0));
float pageOffsetDown = pageDeformOffset(position - vec3(0.0, pageNormalStepY, 0.0));
float pageOffsetUp = pageDeformOffset(position + vec3(0.0, pageNormalStepY, 0.0));
float pageSlopeX = (pageOffsetRight - pageOffsetLeft) / (2.0 * pageNormalStepX);
float pageSlopeY = (pageOffsetUp - pageOffsetDown) / (2.0 * pageNormalStepY);
float pageNormalFacing = objectNormal.z < 0.0 ? -1.0 : 1.0;
objectNormal = normalize(
  vec3(-pageSlopeX * pageNormalFacing, -pageSlopeY * pageNormalFacing, pageNormalFacing)
);

#ifdef USE_TANGENT
  vec3 objectTangent = vec3(tangent.xyz);
#endif
