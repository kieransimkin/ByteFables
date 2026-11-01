Shader "ByteFables/Premultiplied Array"
{
    Properties
    {
        _Array ("Verified texture bank", 2DArray) = "" {}
        _Layer ("Array layer", Float) = 0
        _Mip ("Mip (-1 = automatic)", Float) = -1
    }
    SubShader
    {
        Tags { "Queue"="Transparent" "RenderType"="Transparent" }
        Cull Off ZWrite Off ZTest Always
        Blend One OneMinusSrcAlpha
        Pass
        {
            CGPROGRAM
            #pragma vertex vert_img
            #pragma fragment frag
            #pragma target 3.5
            #pragma require 2darray
            #include "UnityCG.cginc"
            UNITY_DECLARE_TEX2DARRAY(_Array);
            float _Layer, _Mip;
            float4 frag(v2f_img input) : SV_Target
            {
                // CPU upload has already reversed top-origin rows once. Do not flip UVs again.
                float3 uv = float3(input.uv, _Layer);
                if (_Mip >= 0) return UNITY_SAMPLE_TEX2DARRAY_LOD(_Array, uv, _Mip);
                return UNITY_SAMPLE_TEX2DARRAY(_Array, uv);
            }
            ENDCG
        }
    }
    Fallback Off
}
