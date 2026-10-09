// Distribution-only probe against already published production executables.
// All state and result fixtures are synthetic and isolated in a temporary directory.
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
        if(r.Headers.Authorization!=null || r.Headers.Contains("Cookie") || !PublicDownload.AllowedRedirect(r.RequestUri))
            throw new InvalidDataException("Unauthorized transport");
        Count++;return base.SendAsync(r,c);
    }
}
static class PackageProbe {
    static int checks;
    static void Check(bool b,string name){if(!b)throw new InvalidDataException(name);checks++;Console.WriteLine("PASS "+name);}
    static void Reject(Action a,string name){bool rejected=false;try{a();}catch(InvalidDataException){rejected=true;}Check(rejected,name);}
    static string RunChild(string mode, string root, Release next, long sequence) {
        string quote = "\"";
        var info = new System.Diagnostics.ProcessStartInfo(System.Reflection.Assembly.GetExecutingAssembly().Location,
            "apply-child "+mode+" "+quote+root+quote+" "+next.releaseId+" "+next.appVersion+" "+sequence) {
            UseShellExecute=false, RedirectStandardOutput=true, RedirectStandardError=true };
        using(var process=System.Diagnostics.Process.Start(info)) {
            string output=process.StandardOutput.ReadToEnd(),error=process.StandardError.ReadToEnd();process.WaitForExit();
            Console.Write(output);Console.Write(error);
            if(process.ExitCode!=0)throw new InvalidDataException("Isolated apply failed: "+mode);
            return output;
        }
    }
    static int ApplyChild(string[] args) {
        string mode=args[1];var store=new ReleaseStore(args[2]);
        // The real Host writes pending metadata; a separate Launcher process applies it.
        // Every rejection and valid apply starts with independent CLR/reflection state.
        var current=PackagePolicy.VerifyDirectory(store.PathFor(store.ReadState().active));
        string stage=Path.Combine(store.Root,"stage-"+Guid.NewGuid().ToString("N"));
        if(mode!="valid") {
            string expected=mode=="signature"?"Release signature verification failed.":
                mode=="package"?"Pending package is not signed and approved.":"The downloaded update changed.";
            try { OnlinePackage.ExtractPending(store.Root,current,stage); }
            catch(InvalidDataException error) {
                if(error.Message!=expected)throw new InvalidDataException("Wrong rejection: "+error.Message);
                Console.WriteLine("REJECTED="+mode);return 0;
            }
            throw new InvalidDataException("Tampering accepted: "+mode);
        }
        var verified=OnlinePackage.ExtractPending(store.Root,current,stage);
        Check(verified.releaseId==args[3],"signed staging");store.Commit(stage,verified,"update");
        Check(store.ReadState().active==args[3] && store.ReadState().previous==current.releaseId,"apply and recovery pointer");
        Check(PackagePolicy.VerifyDirectory(store.PathFor(args[3])).appVersion==args[4],"installed integrity");
        store.Rollback();Check(store.ReadState().active==current.releaseId,"rollback");
        Check(File.ReadAllText(Path.Combine(store.Root,"synthetic-settings.txt"))=="settings" && File.ReadAllText(Path.Combine(store.Root,"synthetic-result.txt"))=="result","settings and results preserved");
        Check(SignedUpdates.ReadHistory(File.ReadAllText(SignedUpdates.CachePath(store.Root))).sequence==long.Parse(args[5]),"anti-rollback history preserved");
        Console.WriteLine("APPLY_CHECKS="+checks);return 0;
    }
    static async Task<int> Main(string[] args){
        if(args.Length>0 && args[0]=="apply-child")return ApplyChild(args);
        var old=PackagePolicy.VerifyDirectory(args[0]);var next=PackagePolicy.VerifyDirectory(args[1]);
        var registry=Json.Read<RepositoryRegistry>(File.ReadAllText(Path.Combine(args[0],"module-sources.json")));
        string envelope=File.ReadAllText(args[2]),previous=File.ReadAllText(args[3]);
        var signed=SignedUpdates.Verify(envelope,previous,DateTimeOffset.UtcNow);
        Check(signed.catalog.appVersion==next.appVersion,"production-key signature and version");
        Check(SignedUpdates.Verify(envelope,envelope,DateTimeOffset.UtcNow).sequence==signed.sequence,"same signature accepted");
        Reject(()=>SignedUpdates.Verify(previous,envelope,DateTimeOffset.UtcNow),"sequence rollback rejected");
        var changed=Json.Read<SignedEnvelope>(envelope);var bytes=Convert.FromBase64String(changed.signature);bytes[0]^=1;changed.signature=Convert.ToBase64String(bytes);
        Reject(()=>SignedUpdates.Verify(Json.Write(changed),previous,DateTimeOffset.UtcNow),"signature tampering rejected");
        Func<string,Task<ApiResponse>> feed=url=>{if(url!=SignedUpdates.FeedUrl)throw new Exception("Feed URL");return Task.FromResult(new ApiResponse{status=200,body=envelope});};
        bool accepted=false;
        var available=await PublicUpdateCheck.Run(old,registry,previous,feed,(text,c)=>{accepted=text==envelope;},"online");
        Check(available.state=="available" && available.downloadAvailable && !available.requiresSetup && accepted,"previous version accepts online transition without Setup");
        var nextRegistry=Json.Read<RepositoryRegistry>(File.ReadAllText(Path.Combine(args[1],"module-sources.json")));
        var current=await PublicUpdateCheck.Run(next,nextRegistry,envelope,feed,(text,c)=>{},"online");
        Check(current.state=="current" && !current.downloadAvailable,"new version reports current");
        var package=OnlinePackage.Select(signed.catalog,old,registry);
        Check(package!=null && package.profile==old.profile && old.profile==DistributionProfile.Id && package.releaseId==next.releaseId,"signed package selection");
        string work=Path.Combine(Path.GetTempPath(),"suite-distribution-probe-"+Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(work);
        try{
            var store=new ReleaseStore(Path.Combine(work,"data"));store.InstallSeed(args[0]);
            Directory.CreateDirectory(Path.Combine(store.Root,"Updates"));
            Directory.CreateDirectory(Path.GetDirectoryName(SignedUpdates.CachePath(store.Root)));
            File.WriteAllText(SignedUpdates.CachePath(store.Root),envelope);
            File.WriteAllText(Path.Combine(store.Root,"synthetic-settings.txt"),"settings");
            File.WriteAllText(Path.Combine(store.Root,"synthetic-result.txt"),"result");
            string id=Guid.NewGuid().ToString("N"),download=OnlinePackage.DownloadPath(store.Root,id);
            var handler=new AnonymousTransport();
            using(var client=new HttpClient(handler){Timeout=TimeSpan.FromMinutes(3)})
            using(var response=await PublicDownload.Open(client,package,CancellationToken.None)){
                Check((int)response.StatusCode==200 && handler.Count>=1 && handler.Count<=6,"anonymous production download");
                using(var stream=await response.Content.ReadAsStreamAsync())await OnlinePackage.Copy(stream,download,package,null,CancellationToken.None);
            }
            Check(new FileInfo(download).Length==package.bytes && PackagePolicy.HashFile(download)==package.sha256,"download length and SHA-256");
            var pending=new PendingUpdate{id=id,fromRelease=old.releaseId,package=package,modules=signed.catalog.modules,signedEnvelope=envelope};
            string good=Json.Write(pending);File.WriteAllText(OnlinePackage.PendingPath(store.Root),good);
            pending.signedEnvelope=Json.Write(changed);File.WriteAllText(OnlinePackage.PendingPath(store.Root),Json.Write(pending));
            Check(RunChild("signature",store.Root,next,signed.sequence).Contains("REJECTED=signature"),"pending signature tampering rejected");
            pending=Json.Read<PendingUpdate>(good);pending.package.sha256=new string('0',64);File.WriteAllText(OnlinePackage.PendingPath(store.Root),Json.Write(pending));
            Check(RunChild("package",store.Root,next,signed.sequence).Contains("REJECTED=package"),"pending package substitution rejected");
            File.WriteAllText(OnlinePackage.PendingPath(store.Root),good);
            byte first;using(var f=new FileStream(download,FileMode.Open,FileAccess.ReadWrite)){first=(byte)f.ReadByte();f.Position=0;f.WriteByte((byte)(first^1));}
            Check(RunChild("bytes",store.Root,next,signed.sequence).Contains("REJECTED=bytes"),"download tampering rejected");
            using(var f=new FileStream(download,FileMode.Open,FileAccess.Write)){f.WriteByte(first);}
            string applied=RunChild("valid",store.Root,next,signed.sequence);
            if(!applied.Contains("APPLY_CHECKS=6"))throw new InvalidDataException("Incomplete isolated apply checks");
            checks+=6;
        }finally{Directory.Delete(work,true);}
        Console.WriteLine("CHECKS="+checks);return 0;
    }
}

