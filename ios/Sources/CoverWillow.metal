#include <metal_stdlib>
using namespace metal;

// White-matte extraction: return premultiplied transparent watercolor, not paper pixels.
[[ stitchable ]] half4 coverWillowCutout(float2 position, half4 color) {
    // SwiftUI supplies premultiplied color, including transparent black outside the image.
    // Preserve that coverage: treating transparent black as opaque ink creates moving edge bands.
    float coverage = float(color.a);
    if (coverage <= 0.0001) return half4(0);
    float3 matte = clamp(float3(color.rgb) / coverage, 0.0, 1.0);
    float alpha = 1.0 - min(matte.r, min(matte.g, matte.b));
    if (alpha <= 0.001) return half4(0);
    float3 ink = clamp((matte - float3(1.0 - alpha)) / alpha, 0.0, 1.0);
    ink = mix(float3(dot(ink, float3(0.2126, 0.7152, 0.0722))), ink, 0.54);
    ink = mix(ink, float3(0.30, 0.32, 0.23), 0.12);
    alpha *= smoothstep(0.01, 0.065, alpha) * 0.56 * coverage;
    return half4(half3(ink * alpha), half(alpha));
}

[[ stitchable ]] half4 coverOriginalLower(float2 position, half4 color, float2 size, float4 crop) {
    float2 uv = crop.xy + position / max(size, float2(1.0)) * crop.zw;
    return color * half(smoothstep(0.63, 0.67, uv.y));
}

// Rig in original-image coordinates. Roots are fixed and tip weights never fade back to zero.
// Continuous weights let intersecting watercolor twigs share a texture without visible cut seams.
[[ stitchable ]] float2 coverWillowBranches(float2 position, float2 size, float4 crop, float time) {
    float2 uv = crop.xy + position / max(size, float2(1.0)) * crop.zw;
    float root = mix(0.18, 0.035, smoothstep(0.0, 0.40, uv.x));
    float tip = mix(0.63, 0.49, smoothstep(0.32, 0.70, uv.x));
    tip = mix(tip, 0.24, smoothstep(0.72, 1.0, uv.x));
    float along = clamp((uv.y - root) / (tip - root), 0.0, 1.0);
    float phase = 1.05 * smoothstep(0.15, 0.42, uv.x) + 0.8 * smoothstep(0.58, 0.87, uv.x);
    float wind = 0.78 * sin(time * 0.42 - along * 0.55 + phase)
               + 0.22 * sin(time * 0.67 - along * 0.35 + phase * 0.5);
    float sway = min(19.0, size.x * 0.048) * along * along * wind * smoothstep(0.0, 3.0, time);
    return position + float2(sway, sway * sway / 300.0 * along);
}
