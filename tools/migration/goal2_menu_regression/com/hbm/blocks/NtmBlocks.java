package com.hbm.blocks;
import com.hbm.blocks.machine.NTMAnvilBlock;
public class NtmBlocks {
 public static final Holder<NTMAnvilBlock> ANVIL = new Holder<>(new NTMAnvilBlock());
 public record Holder<T>(T value) { public T get(){return value;} }
}
