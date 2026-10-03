// First public User release: production signature/download/install; synthetic local state only.
using System;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using Ecuss.Desktop;
sealed class BootstrapTransport:DelegatingHandler {
 public int Count;
 public BootstrapTransport():base(new HttpClientHandler{AllowAutoRedirect=false,UseCookies=false,UseDefaultCredentials=false}){}
 protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage r,CancellationToken c){
  if(r.Headers.Authorization!=null || r.Headers.Contains("Cookie") || !PublicDownload.AllowedRedirect(r.RequestUri))throw new InvalidDataException("Credential/destination");
  Count++;return base.SendAsync(r,c);
 }
}
static class UserBootstrapProbe {
 static int checks;
 static void Check(bool b,string name){if(!b)throw new InvalidDataException(name);checks++;Console.WriteLine("PASS "+name);}
 static void Reject(Action a,string name){bool rejected=false;try{a();}catch(InvalidDataException){rejected=true;}Check(rejected,name);}
 static async Task<int> Main(string[] args){
  var next=PackagePolicy.VerifyDirectory(args[0]);var registry=Json.Read<RepositoryRegistry>(File.ReadAllText(Path.Combine(args[0],"module-sources.json")));
  string envelope=File.ReadAllText(args[1]),previous=File.ReadAllText(args[2]);var signed=SignedUpdates.Verify(envelope,previous,DateTimeOffset.UtcNow);
  Check(next.profile=="user" && DistributionProfile.Id=="user","actual User assembly and package");
  Check(signed.catalog.appVersion==next.appVersion && signed.catalog.profiles.SequenceEqual(new[]{"master","user"}),"one production signature covers both profiles");
  Check(SignedUpdates.Verify(envelope,envelope,DateTimeOffset.UtcNow).sequence==signed.sequence,"same signature accepted");
  Reject(()=>SignedUpdates.Verify(previous,envelope,DateTimeOffset.UtcNow),"sequence rollback rejected");
  var changed=Json.Read<SignedEnvelope>(envelope);var bytes=Convert.FromBase64String(changed.signature);bytes[0]^=1;changed.signature=Convert.ToBase64String(bytes);
  Reject(()=>SignedUpdates.Verify(Json.Write(changed),previous,DateTimeOffset.UtcNow),"signature tampering rejected");
  Func<string,Task<ApiResponse>> feed=url=>{if(url!=SignedUpdates.FeedUrl)throw new Exception("Feed");return Task.FromResult(new ApiResponse{status=200,body=envelope});};
  var current=await PublicUpdateCheck.Run(next,registry,envelope,feed,(text,c)=>{},"online");
  Check(current.state=="current" && !current.downloadAvailable,"User reads shared current feed");
  var package=signed.catalog.packages.Single(x=>x.profile=="user");OnlinePackage.Validate(package,registry);
  Check(package.releaseId==next.releaseId,"User selects its approved release");
  Reject(()=>OnlinePackage.Validate(signed.catalog.packages.Single(x=>x.profile=="master"),registry),"Master package rejected by User");
  string work=Path.Combine(Path.GetTempPath(),"suite-user-bootstrap-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(work);
  try{
   string download=Path.Combine(work,"download.zip");var handler=new BootstrapTransport();
   using(var client=new HttpClient(handler){Timeout=TimeSpan.FromMinutes(3)})using(var response=await PublicDownload.Open(client,package,CancellationToken.None)){
    Check((int)response.StatusCode==200 && handler.Count>=1 && handler.Count<=6,"anonymous User package download");
    using(var stream=await response.Content.ReadAsStreamAsync())await OnlinePackage.Copy(stream,download,package,null,CancellationToken.None);
   }
   Check(new FileInfo(download).Length==package.bytes && PackagePolicy.HashFile(download)==package.sha256,"User download hash/length");
   string unpacked=Path.Combine(work,"unpacked");var release=PackagePolicy.ExtractZip(download,unpacked);OnlinePackage.VerifyRelease(release,package,signed.catalog.modules);
   Check(release.releaseId==next.releaseId,"User extracted integrity/modules");
   var store=new ReleaseStore(Path.Combine(work,"data"));store.InstallSeed(unpacked);
   Check(store.ReadState().active==next.releaseId,"User first installation");
   File.WriteAllText(Path.Combine(store.Root,"synthetic-settings.txt"),"settings");File.WriteAllText(Path.Combine(store.Root,"synthetic-result.txt"),"result");
   Directory.CreateDirectory(Path.GetDirectoryName(SignedUpdates.CachePath(store.Root)));File.WriteAllText(SignedUpdates.CachePath(store.Root),envelope);
   store.InstallSeed(unpacked);
   Check(store.ReadState().active==next.releaseId && PackagePolicy.VerifyDirectory(store.PathFor(next.releaseId)).profile=="user","User reinstall integrity");
   Check(File.ReadAllText(Path.Combine(store.Root,"synthetic-settings.txt"))=="settings" && File.ReadAllText(Path.Combine(store.Root,"synthetic-result.txt"))=="result","User settings/results preserved");
   Check(SignedUpdates.ReadHistory(File.ReadAllText(SignedUpdates.CachePath(store.Root))).sequence==signed.sequence,"User anti-rollback history retained");
  }finally{Directory.Delete(work,true);}
  Console.WriteLine("CHECKS="+checks);return 0;
 }
}
