Shader "ByteFables/PremultipliedArrayHDRP"
{
    Properties { _Array("Array", 2DArray) = "" {} _Layer("Layer", Float)=0 _Mip("Mip", Float)=0 }
    SubShader
    {
        Tags { "RenderPipeline"="HDRenderPipeline" "Queue"="Transparent" "RenderType"="Transparent" }
        Pass
        {
            Name "ByteFablesHDRP" Tags { "LightMode"="ForwardOnly" }
            Blend One OneMinusSrcAlpha ZWrite Off ZTest Always Cull Off
            HLSLPROGRAM
            #pragma target 4.5
            #pragma require 2darray
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"
            UNITY_DECLARE_TEX2DARRAY(_Array); float _Layer; float _Mip;
            struct appdata { float4 vertex:POSITION; float2 uv:TEXCOORD0; };
            struct v2f { float4 pos:SV_POSITION; float2 uv:TEXCOORD0; };
            v2f vert(appdata v){v2f o;o.pos=UnityObjectToClipPos(v.vertex);o.uv=v.uv;return o;}
            half4 frag(v2f i):SV_Target{return UNITY_SAMPLE_TEX2DARRAY_LOD(_Array,float3(i.uv,_Layer),_Mip);}
            ENDHLSL
        }
    }
}
