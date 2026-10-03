// Explicitly approved one-time import transition. Compiled against the actual old binary.
// Online rejection is a required assertion, never silently bypassed or called online success.
using System;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using Ecuss.Desktop;
sealed class AnonymousTransport:DelegatingHandler {
    public int Count;
    public AnonymousTransport():base(new HttpClientHandler{AllowAutoRedirect=false,UseCookies=false,UseDefaultCredentials=false}){}
    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage r,CancellationToken c){
        if(r.Headers.Authorization!=null||r.Headers.Contains("Cookie")||!PublicDownload.AllowedRedirect(r.RequestUri))throw new InvalidDataException("Unauthorized transport");
        Count++;return base.SendAsync(r,c);
    }
}
static class LegacyImportProbe {
    static int checks;
    static void Check(bool b,string name){if(!b)throw new InvalidDataException(name);checks++;Console.WriteLine("PASS "+name);}
    static void Reject(Action a,string name){bool rejected=false;try{a();}catch(InvalidDataException){rejected=true;}Check(rejected,name);}
    static async Task<int> Main(string[] args){
        var old=PackagePolicy.VerifyDirectory(args[0]);var next=PackagePolicy.VerifyDirectory(args[1]);
        var registry=Json.Read<RepositoryRegistry>(File.ReadAllText(Path.Combine(args[0],"module-sources.json")));
        var nextRegistry=Json.Read<RepositoryRegistry>(File.ReadAllText(Path.Combine(args[1],"module-sources.json")));
        string envelope=File.ReadAllText(args[2]),previous=File.ReadAllText(args[3]);
        var signed=SignedUpdates.Verify(envelope,previous,DateTimeOffset.UtcNow);
        Check(signed.catalog.appVersion==next.appVersion,"production-key signature and version");
        Check(SignedUpdates.Verify(envelope,envelope,DateTimeOffset.UtcNow).sequence==signed.sequence,"same signature accepted");
        Reject(()=>SignedUpdates.Verify(previous,envelope,DateTimeOffset.UtcNow),"sequence rollback rejected");
        var changed=Json.Read<SignedEnvelope>(envelope);var bytes=Convert.FromBase64String(changed.signature);bytes[0]^=1;changed.signature=Convert.ToBase64String(bytes);
        Reject(()=>SignedUpdates.Verify(Json.Write(changed),previous,DateTimeOffset.UtcNow),"signature tampering rejected");
        Func<string,Task<ApiResponse>> feed=url=>{if(url!=SignedUpdates.FeedUrl)throw new Exception("Feed URL");return Task.FromResult(new ApiResponse{status=200,body=envelope});};
        bool accepted=false;var unavailable=await PublicUpdateCheck.Run(old,registry,previous,feed,(text,c)=>accepted=true,"online");
        Check(unavailable.state=="invalidCatalog"&&!unavailable.downloadAvailable&&!accepted,"legacy online new-module restriction reproduced; one import required");
        var current=await PublicUpdateCheck.Run(next,nextRegistry,envelope,feed,(text,c)=>{},"online");
        Check(current.state=="current"&&!current.downloadAvailable,"imported latest release metadata reports current");
        var package=signed.catalog.packages.Single(p=>p.profile=="master");OnlinePackage.Validate(package,registry);
        Check(package.releaseId==next.releaseId&&package.appVersion==next.appVersion,"reviewed full package identified by authenticated metadata");
        changed=Json.Read<SignedEnvelope>(envelope);bytes=Convert.FromBase64String(changed.payload);bytes[0]^=1;changed.payload=Convert.ToBase64String(bytes);
        Reject(()=>SignedUpdates.Verify(Json.Write(changed),previous,DateTimeOffset.UtcNow),"payload substitution rejected");
        string work=Path.Combine(Path.GetTempPath(),"suite-legacy-import-probe-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(work);
        try{
            var store=new ReleaseStore(Path.Combine(work,"data"));store.InstallSeed(args[0]);
            Directory.CreateDirectory(Path.GetDirectoryName(SignedUpdates.CachePath(store.Root)));File.WriteAllText(SignedUpdates.CachePath(store.Root),envelope);
            File.WriteAllText(Path.Combine(store.Root,"synthetic-settings.txt"),"settings");File.WriteAllText(Path.Combine(store.Root,"synthetic-result.txt"),"result");
            string download=Path.Combine(work,"download.zip");var handler=new AnonymousTransport();
            using(var client=new HttpClient(handler){Timeout=TimeSpan.FromMinutes(3)})using(var response=await PublicDownload.Open(client,package,CancellationToken.None)){
                Check((int)response.StatusCode==200&&handler.Count>=1&&handler.Count<=6,"anonymous production download");
                using(var stream=await response.Content.ReadAsStreamAsync())await OnlinePackage.Copy(stream,download,package,null,CancellationToken.None);
            }
            Check(new FileInfo(download).Length==package.bytes&&PackagePolicy.HashFile(download)==package.sha256,"download length and SHA-256");
            var wrong=Json.Read<PublishedPackage>(Json.Write(package));wrong.sha256=new string('0',64);
            Reject(()=>{using(var stream=File.OpenRead(download))OnlinePackage.Copy(stream,Path.Combine(work,"bad.zip"),wrong,null,CancellationToken.None).GetAwaiter().GetResult();},"substituted package hash rejected by legacy download verifier");
            string stage=Path.Combine(work,"stage");var verified=PackagePolicy.ExtractZip(download,stage);OnlinePackage.VerifyRelease(verified,package,signed.catalog.modules);
            Check(verified.releaseId==next.releaseId,"one full imported package matches signed modules and complete inventory");
            Check(WorkAccess.SupportsPolicy(verified),"existing import compatibility policy satisfied");
            store.Commit(stage,verified,"update");
            Check(store.ReadState().active==next.releaseId&&store.ReadState().previous==old.releaseId&&store.ReadState().history.Count==2,"direct import without intermediate release and recovery pointer");
            Check(PackagePolicy.VerifyDirectory(store.PathFor(next.releaseId)).appVersion==next.appVersion,"installed integrity");
            store.Rollback();Check(store.ReadState().active==old.releaseId,"rollback to actual prior version");
            Check(File.ReadAllText(Path.Combine(store.Root,"synthetic-settings.txt"))=="settings"&&File.ReadAllText(Path.Combine(store.Root,"synthetic-result.txt"))=="result","settings and saved results preserved");
            Check(SignedUpdates.ReadHistory(File.ReadAllText(SignedUpdates.CachePath(store.Root))).sequence==signed.sequence,"anti-rollback signature history retained");
        }finally{Directory.Delete(work,true);}
        Console.WriteLine("CHECKS="+checks);return 0;
    }
}
