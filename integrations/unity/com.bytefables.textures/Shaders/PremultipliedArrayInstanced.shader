Shader "ByteFables/Premultiplied Array Instanced"
{
    Properties
    {
        _Array ("Verified texture bank", 2DArray) = "" {}
        _Mip ("Exact mip", Float) = 0
    }
    SubShader
    {
        Tags { "Queue"="Transparent" "RenderType"="Transparent" }
        Cull Off ZWrite Off ZTest Always
        Blend One OneMinusSrcAlpha
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma require 2darray
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            UNITY_DECLARE_TEX2DARRAY(_Array);
            float _Mip;
            UNITY_INSTANCING_BUFFER_START(ByteFablesInstances)
                UNITY_DEFINE_INSTANCED_PROP(float4, _Rect)
                UNITY_DEFINE_INSTANCED_PROP(float, _Layer)
            UNITY_INSTANCING_BUFFER_END(ByteFablesInstances)
            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 position : SV_POSITION;
                float2 uv : TEXCOORD0;
                float layer : TEXCOORD1;
            };
            v2f vert(appdata input)
            {
                UNITY_SETUP_INSTANCE_ID(input);
                float4 rect = UNITY_ACCESS_INSTANCED_PROP(ByteFablesInstances, _Rect);
                v2f output;
                output.position = float4(lerp(rect.xy, rect.zw, input.vertex.xy), 0, 1);
                output.uv = input.uv;
                output.layer = UNITY_ACCESS_INSTANCED_PROP(ByteFablesInstances, _Layer);
                return output;
            }
            float4 frag(v2f input) : SV_Target
            {
                return UNITY_SAMPLE_TEX2DARRAY_LOD(_Array, float3(input.uv, input.layer), _Mip);
            }
            ENDCG
        }
    }
    Fallback Off
}
