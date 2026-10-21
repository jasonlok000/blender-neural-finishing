"""Private, process-local experimental NVAPI architecture adapter.
No driver file, registry value, system DLL or persistent system state is changed.
The hook is removed on close; only the selected RTX3090 handle is adapted.
Uses the public NV_GPU_ARCH_INFO layout. Not evidence that compute kernels work.
"""
import ctypes,struct
class Arch(ctypes.Structure):
 _fields_=[('version',ctypes.c_uint32),('architecture',ctypes.c_uint32),('implementation',ctypes.c_uint32),('revision',ctypes.c_uint32)]
class ProbeHook:
 def __init__(self):
  self.api=ctypes.WinDLL('C:/Windows/System32/nvapi64.dll');qi=self.api.nvapi_QueryInterface;qi.argtypes=[ctypes.c_uint32];qi.restype=ctypes.c_void_p;init=ctypes.CFUNCTYPE(ctypes.c_int)(qi(0x0150E828));assert init()==0
  enum=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(ctypes.c_uint32))(qi(0xE5AC921F));handles=(ctypes.c_void_p*64)();n=ctypes.c_uint32();assert enum(handles,ctypes.byref(n))==0 and n.value==1,'This probe is restricted to the current single-NVIDIA-GPU setup'
  self.handle=handles[0];self.address=qi(0xD8265D24);original=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.c_void_p,ctypes.POINTER(Arch))(self.address);cached=Arch(ctypes.sizeof(Arch)|(1<<16),0,0,0);assert original(self.handle,ctypes.byref(cached))==0;assert cached.architecture&0xFFFFFFF0==0x170,hex(cached.architecture)
  self.real=[cached.architecture,cached.implementation,cached.revision];self.calls=0
  def callback(handle,result):
   if not result or handle!=self.handle:return -5
   version=result.contents.version
   if version&0xFFFF!=ctypes.sizeof(Arch):return -9
   result.contents.architecture=0x1B0;result.contents.implementation=3;result.contents.revision=0xA1;self.calls+=1;return 0
  self.callback=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.c_void_p,ctypes.POINTER(Arch))(callback);self.saved=ctypes.string_at(self.address,12);self.k=ctypes.WinDLL('kernel32',use_last_error=True);self.k.VirtualProtect.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint32,ctypes.POINTER(ctypes.c_uint32)];self.k.VirtualProtect.restype=ctypes.c_int;self.k.FlushInstructionCache.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t];self.k.GetCurrentProcess.restype=ctypes.c_void_p;self._write(b'\x48\xb8'+struct.pack('<Q',ctypes.cast(self.callback,ctypes.c_void_p).value)+b'\xff\xe0')
 def _write(self,data):
  old=ctypes.c_uint32();assert self.k.VirtualProtect(self.address,len(data),0x40,ctypes.byref(old));ctypes.memmove(self.address,data,len(data));dummy=ctypes.c_uint32();assert self.k.VirtualProtect(self.address,len(data),old.value,ctypes.byref(dummy));self.k.FlushInstructionCache(self.k.GetCurrentProcess(),self.address,len(data))
 def close(self):self._write(self.saved)
