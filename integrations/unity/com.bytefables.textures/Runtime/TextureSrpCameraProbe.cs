using System;
using System.Collections;
using ByteFables.Textures.Core;
using UnityEngine;

namespace ByteFables.Textures
{
    /// <summary>Renders selected imported array slices through an actual URP/HDRP Camera.Render pass.</summary>
    public static class TextureSrpCameraProbe
    {
        static void Require(bool ok,string message){if(!ok)throw new TextureContractException(message);}
        static void Same(byte[] a,byte[] b,string label,int tolerance=1){Require(a.Length==b.Length,label+": length mismatch");for(int i=0;i<a.Length;i++)Require(Math.Abs(a[i]-b[i])<=tolerance,label+": pixel mismatch at "+i);}
        static byte[] Composite(byte[] source,Color32 matte){var r=new byte[source.Length];byte[] bg={matte.r,matte.g,matte.b,matte.a};for(int p=0;p<source.Length;p+=4)for(int c=0;c<4;c++)r[p+c]=(byte)(source[p+c]+(bg[c]*(255-source[p+3])+127)/255);return r;}
        static Mesh Quad(){var m=new Mesh{name="ByteFables SRP camera quad"};m.vertices=new[]{new Vector3(-1,-1,0),new Vector3(1,-1,0),new Vector3(1,1,0),new Vector3(-1,1,0)};m.uv=new[]{new Vector2(0,0),new Vector2(1,0),new Vector2(1,1),new Vector2(0,1)};m.triangles=new[]{0,1,2,0,2,3};m.UploadMeshData(false);return m;}
        static byte[] Render(Camera camera,Material material,int side,Color32 matte)
        {
            var target=new RenderTexture(side,side,0,RenderTextureFormat.ARGB32,RenderTextureReadWrite.Linear){antiAliasing=1,useMipMap=false,autoGenerateMips=false,filterMode=FilterMode.Point};var read=new Texture2D(side,side,TextureFormat.RGBA32,false,true);var prev=RenderTexture.active;bool srgb=GL.sRGBWrite;
            try{Require(target.Create(),"SRP camera target allocation failed");camera.targetTexture=target;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=matte;GL.sRGBWrite=false;camera.Render();RenderTexture.active=target;read.ReadPixels(new Rect(0,0,side,side),0,0,false);return read.GetPixelData<byte>(0).ToArray();}
            finally{camera.targetTexture=null;RenderTexture.active=prev;GL.sRGBWrite=srgb;target.Release();TextureArrayUpload.Destroy(target);TextureArrayUpload.Destroy(read);}
        }
        static int[] Samples(int count,int total){if(count>=total){var all=new int[total];for(int i=0;i<total;i++)all[i]=i;return all;}var result=new int[count];for(int i=0;i<count;i++)result[i]=(int)Math.Round(i*(total-1.0)/(count-1.0));return result;}
        public static IEnumerator Qualify(TextureBundleAsset imported,TextureBundleData data,TextureBundleAsset sentinel,TextureBundleData probes,Shader shader,int sourceSamples,TextureSrpResult report)
        {
            Require(imported!=null&&sentinel!=null&&shader!=null&&shader.isSupported,"SRP camera inputs unavailable");var mesh=Quad();var go=new GameObject("ByteFables SRP camera surface");go.layer=31;var filter=go.AddComponent<MeshFilter>();filter.sharedMesh=mesh;var renderer=go.AddComponent<MeshRenderer>();var material=new Material(shader);renderer.sharedMaterial=material;var cameraObject=new GameObject("ByteFables SRP camera");var camera=cameraObject.AddComponent<Camera>();camera.transform.position=new Vector3(0,0,-2);camera.transform.rotation=Quaternion.identity;camera.orthographic=true;camera.orthographicSize=1;camera.aspect=1;camera.nearClipPlane=.1f;camera.farClipPlane=4;camera.cullingMask=1<<31;camera.allowHDR=false;camera.allowMSAA=false;
            try
            {
                foreach(var tuple in new[]{new object[]{imported,data,Samples(sourceSamples,data.Sprites.Count)},new object[]{sentinel,probes,Samples(probes.Sprites.Count,probes.Sprites.Count)}})
                {
                    var asset=(TextureBundleAsset)tuple[0];var source=(TextureBundleData)tuple[1];var indices=(int[])tuple[2];
                    foreach(int index in indices){var sprite=source.Sprites[index];var bank=asset.GetBank(sprite.BankIndex);bank.filterMode=FilterMode.Point;bank.wrapMode=TextureWrapMode.Clamp;material.SetTexture("_Array",bank);material.SetFloat("_Layer",sprite.LayerIndex);
                        for(int mip=0;mip<source.Banks[sprite.BankIndex].LevelCount;mip++){material.SetFloat("_Mip",mip);int side=source.Banks[sprite.BankIndex].LevelSize(mip);var expected=source.Banks[sprite.BankIndex].CopyLayer(mip,sprite.LayerIndex,true);foreach(var matte in new[]{new Color32(0,0,0,0),new Color32(0,0,0,255),new Color32(255,255,255,255)}){Same(Composite(expected,matte),Render(camera,material,side,matte),"SRP Camera.Render",1);report.pipelineComparisons++;}yield return null;}
                    }
                }
            }
            finally{TextureArrayUpload.Destroy(material);TextureArrayUpload.Destroy(cameraObject);TextureArrayUpload.Destroy(go);TextureArrayUpload.Destroy(mesh);}
        }
    }
}
