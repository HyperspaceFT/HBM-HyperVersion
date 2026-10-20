package com.hbm.items.machine;

import com.hbm.blockentity.machine.rbmk.IRBMKFluxReceiver.NType;
import com.hbm.blockentity.machine.rbmk.RBMKDials;
import com.hbm.util.TagsUtil;
import net.minecraft.ChatFormatting;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.util.Mth;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.function.BiFunction;
import java.util.function.Function;

/**
 * Port of the original com.hbm.items.machine.ItemRBMKRod (HBM's Nuclear Tech). The rod state is kept in custom data as the double
 * values "yield", "xenon", "core" and "hull" (the original NBT keys); the RBMK fuel column (Goal24C) saves whole stacks, so these keys
 * are a persistence schema. Only the regular tooltip is ported; the DRX branch (:451-473) is deferred with rbmk_fuel_drx.
 */
public class RBMKRodItem extends Item {

    public RBMKPelletItem pellet;
    public double reactivity;               //endpoint of the function
    public double selfRate;                 //self-inflicted flux from self-igniting fuels
    public EnumBurnFunc function = EnumBurnFunc.LOG_TEN;
    public EnumDepleteFunc depFunc = EnumDepleteFunc.GENTLE_SLOPE;
    public double xGen = 0.5D;              //multiplier for xenon production
    public double xBurn = 50D;              //divider for xenon burnup
    public double heat = 1D;                //heat produced per outFlux
    public double yield;                    //total potential inFlux the rod can take in its lifetime
    public double meltingPoint = 1000D;     //the maximum heat of the rod's hull before shit hits the fan. the core can be as hot as it wants to be
    public double diffusion = 0.02D;        //the speed at which the core heats the hull
    public NType nType = NType.SLOW;        //neutronType, the most efficient neutron type for fission
    public NType rType = NType.FAST;        //releaseType, the type of neutrons released by this fuel
    public int colorTint = 0x304825;        //RGB color of the rod when rendered in the fuel channel
    public double heatCoeffStart = 0D;      //when the heat coefficient starts acting
    public double heatCoeffLength = 0D;     //when the reaction multiplier of the coefficient hits 0 after taking effect

    /*   _____
     * ,I I I I,
     * |'-----'|
     * |       |
     *  '-----'
     *  I I I I
     *  I I I I
     *  I I I I
     *  I I I I
     *  I I I I
     *  I I I I
     * ,I I I I,
     * |'-----'|
     * |       |
     *  '-----'
     *  I I I I
     *
     *  i drew a fuel rod yay
     */

    /** Original craftableRods (:63): every rod made from a pellet, in construction order. */
    public static final List<RBMKRodItem> CRAFTABLE_RODS = new ArrayList<>();

    // The original's full name string (:26) is the pellet's fullName language key here, see RBMKPelletItem#getFullNameKey.
    // Stack size 1 and the empty rod as crafting remainder (:75-76) are set on the properties in NtmItems.
    public RBMKRodItem(Properties properties, RBMKPelletItem pellet) {
        super(properties);
        this.pellet = pellet;

        CRAFTABLE_RODS.add(this);
    }

    public RBMKRodItem setTint(int tint) {
        this.colorTint = tint;
        return this;
    }

    public RBMKRodItem setYield(double yield) {
        this.yield = yield;
        return this;
    }

    public RBMKRodItem setStats(double funcEnd) {
        return setStats(funcEnd, 0);
    }

    public RBMKRodItem setStats(double funcEnd, double selfRate) {
        this.reactivity = funcEnd;
        this.selfRate = selfRate;
        return this;
    }

    public RBMKRodItem setFunction(EnumBurnFunc func) {
        this.function = func;
        return this;
    }

    public RBMKRodItem setDepletionFunction(EnumDepleteFunc func) {
        this.depFunc = func;
        return this;
    }

    public RBMKRodItem setHeatCoeff(double start, double length) {
        this.heatCoeffStart = start;
        this.heatCoeffLength = length;
        return this;
    }

    public RBMKRodItem setXenon(double gen, double burn) {
        this.xGen = gen;
        this.xBurn = burn;
        return this;
    }

    public RBMKRodItem setHeat(double heat) {
        this.heat = heat;
        return this;
    }

    public RBMKRodItem setDiffusion(double diffusion) {
        this.diffusion = diffusion;
        return this;
    }

    public RBMKRodItem setMeltingPoint(double meltingPoint) {
        this.meltingPoint = meltingPoint;
        return this;
    }

    public RBMKRodItem setNeutronTypes(NType nType, NType rType) {
        this.nType = nType;
        this.rType = rType;
        return this;
    }

    /**
     * Adjusts the input flux using the poison level
     * Generates, then burns poison
     * Calculates the outflux based on influx, enrichment and poison
     * Depletes the yield, then returns the outflux
     * The Level parameter is unused and kept only for parity with the original callers; NEO's RBMKDials read config values and take no world.
     * @param stack
     * @param inFlux
     * @return outFlux
     */
    public double burn(Level level, ItemStack stack, double inFlux) {

        inFlux += selfRate;

        //if xenon poison is enabled
        if(RBMKDials.getXenon()) {
            double xenon = getPoison(stack);
            xenon -= xenonBurnFunc(inFlux);

            inFlux *= (1D - getPoisonLevel(stack));

            xenon += xenonGenFunc(inFlux);

            if(xenon < 0D) xenon = 0D;
            if(xenon > 100D) xenon = 100D;

            setPoison(stack, xenon);
        }

        double mult = 1D;
        double coreHeat = getCoreHeat(stack);

        if(this.heatCoeffStart != 0) {
            if(coreHeat >= this.heatCoeffStart) {
                double prog = (coreHeat - this.heatCoeffStart) / this.heatCoeffLength;
                if(prog > 1) prog = 1;
                mult = Math.sin((prog * Math.PI + Math.PI) / 2);
            }
        }

        double outFlux = reactivityFunc(inFlux, getEnrichment(stack) * mult) * RBMKDials.getReactivityMod();

        //if depletion is enabled
        if(RBMKDials.getDepletion()) {
            double y = getYield(stack);
            y -= inFlux;

            if(y < 0D) y = 0D;

            setYield(stack, y);
        }
        coreHeat += outFlux * heat;

        setCoreHeat(stack, rectify(coreHeat));

        return outFlux;
    }

    private static double rectify(double num) {

        if(num > 1_000_000D) num = 1_000_000D;
        if(num < 20D || Double.isNaN(num)) num = 20D;

        return num;
    }

    /**
     * Heat up the core based on the outFlux, then move some heat to the hull
     * @param stack
     */
    public void updateHeat(Level level, ItemStack stack, double mod) {

        double coreHeat = getCoreHeat(stack);
        double hullHeat = getHullHeat(stack);

        if(coreHeat > hullHeat) {

            double mid = (coreHeat - hullHeat) / 2D;

            coreHeat -= mid * this.diffusion * RBMKDials.getFuelDiffusionMod() * mod;
            hullHeat += mid * this.diffusion * RBMKDials.getFuelDiffusionMod() * mod;

            setCoreHeat(stack, rectify(coreHeat));
            setHullHeat(stack, rectify(hullHeat));
        }
    }

    /**
     * return one tick's worth of heat and cool the hull of the fuel rod, this heat goes into the fuel rod assembly block
     * @param stack
     * @return
     */
    public double provideHeat(Level level, ItemStack stack, double heat, double mod) {

        double hullHeat = getHullHeat(stack);

        //metldown! the hull melts so the entire structure stops making sense
        //hull and core heats are instantly equalized into 33% of their sum each,
        //the rest is sent to the component which is always fatal
        if(hullHeat > this.meltingPoint) {
            double coreHeat = getCoreHeat(stack);
            double avg = (heat + hullHeat + coreHeat) / 3D;
            setCoreHeat(stack, avg);
            setHullHeat(stack, avg);
            return avg - heat;
        }

        if(hullHeat <= heat)
            return 0;

        double ret = (hullHeat - heat) / 2;

        ret *= RBMKDials.getFuelHeatProvision() * mod;

        hullHeat -= ret;
        setHullHeat(stack, hullHeat);

        return ret;
    }

    /**
     * The original titles were hard-coded English (:263-271); NEO keeps their colours and translates trait.rbmk.func.&lt;name&gt;.
     * The value comments are the original's and do not match {@link #reactivityFunc}, which is what the rods actually use.
     */
    public enum EnumBurnFunc {
        PASSIVE(ChatFormatting.DARK_GREEN),     //const, no reactivity
        LOG_TEN(ChatFormatting.YELLOW),         //log10(x + 1) * reactivity * 50
        PLATEU(ChatFormatting.GREEN),           //(1 - e^(-x/25)) * reactivity * 100
        ARCH(ChatFormatting.RED),               //x-(x²/1000) * reactivity
        SIGMOID(ChatFormatting.GREEN),          //100 / (1 + e^(-(x - 50) / 10)) <- tiny amount of reactivity at x=0 !
        SQUARE_ROOT(ChatFormatting.YELLOW),     //sqrt(x) * 10 * reactivity
        LINEAR(ChatFormatting.RED),             //x * reactivity
        QUADRATIC(ChatFormatting.RED),          //x^2 / 100 * reactivity
        EXPERIMENTAL(ChatFormatting.RED);       //x * (sin(x) + 1)

        public final ChatFormatting color;

        EnumBurnFunc(ChatFormatting color) {
            this.color = color;
        }

        public MutableComponent getTitle() {
            return Component.translatable("trait.rbmk.func." + name().toLowerCase(Locale.ROOT)).withStyle(color);
        }
    }

    /**
     * @param enrichment [0;100] ...or at least those are sane levels
     * @return the amount of reactivity yielded, unmodified by xenon
     */
    public double reactivityFunc(double in, double enrichment) {

        double flux = in * reactivityModByEnrichment(enrichment);

        switch(this.function) {
            case PASSIVE: return selfRate * enrichment;
            case LOG_TEN: return Math.log10(flux + 1) * 0.5D * reactivity;
            case PLATEU: return (1 - Math.pow(Math.E, -flux / 25D)) * reactivity;
            case ARCH: return Math.max((flux - (flux * flux / 10000D)) / 100D * reactivity, 0D);
            case SIGMOID: return reactivity / (1 + Math.pow(Math.E, -(flux - 50D) / 10D));
            case SQUARE_ROOT: return Math.sqrt(flux) * reactivity / 10D;
            case LINEAR: return flux / 100D * reactivity;
            case QUADRATIC: return flux * flux / 10000D * reactivity;
            case EXPERIMENTAL: return flux * (Math.sin(flux) + 1) * reactivity;
        }

        return 0;
    }

    /**
     * Original getFuncDescription (:303-342). The format strings became the keys trait.rbmk.funcDesc.&lt;name&gt; with %1$s as the flux
     * and %2$s as the reactivity endpoint; the argument text keeps the original's colour codes.
     */
    public MutableComponent getFuncDescription(ItemStack stack) {

        double enrichment = getEnrichment(stack);
        String flux = selfRate > 0 ? "(x" + ChatFormatting.RED + " + " + selfRate + "" + ChatFormatting.WHITE + ")" : "x";
        String enrichmentPer = null;

        if(enrichment < 1) {
            enrichment = reactivityModByEnrichment(enrichment);
            String enrichmentMod = ChatFormatting.YELLOW + "" + ((int)(enrichment * 1000D) / 1000D) + ChatFormatting.WHITE;
            enrichmentPer = ChatFormatting.GOLD + " (" + ((int)(enrichment * 1000D) / 10D) + "%)";

            flux = "(" + flux + " * " + enrichmentMod + ")";
        }

        MutableComponent function;

        if(this.function == EnumBurnFunc.PASSIVE) {
            function = Component.literal(ChatFormatting.RED + "" + selfRate);
        } else {
            function = Component.translatable("trait.rbmk.funcDesc." + this.function.name().toLowerCase(Locale.ROOT), flux, String.valueOf(reactivity));
        }

        if(enrichmentPer != null) function.append(Component.literal(enrichmentPer));

        return function;
    }

    public enum EnumDepleteFunc {
        LINEAR,         //old function
        RAISING_SLOPE,  //for breeding fuels such as MEU, maximum of 110% at 28% depletion
        BOOSTED_SLOPE,  //for strong breeding fuels such Th232, maximum of 132% at 64% depletion
        GENTLE_SLOPE,   //recommended for most fuels, maximum barely over the start, near the beginning
        STATIC;         //for arcade-style neutron sources
    }

    public double reactivityModByEnrichment(double enrichment) {

        switch(this.depFunc) {
            default:
            case LINEAR: return enrichment;
            case STATIC: return 1D;
            case BOOSTED_SLOPE: return enrichment + Math.sin((enrichment - 1) * (enrichment - 1) * Math.PI); //x + sin([x - 1]^2 * pi) works
            case RAISING_SLOPE: return enrichment + (Math.sin(enrichment * Math.PI) / 2D); //x + (sin(x * pi) / 2) actually works
            case GENTLE_SLOPE: return enrichment + (Math.sin(enrichment * Math.PI) / 3D); //x + (sin(x * pi) / 3) also works
        }
    }

    /**
     * Xenon generated per tick, linear function
     * @param flux
     * @return
     */
    public double xenonGenFunc(double flux) {
        return flux * xGen;
    }

    /**
     * Xenon burned away per tick, quadratic function
     * @param flux
     * @return
     */
    public double xenonBurnFunc(double flux) {
        return (flux * flux) / xBurn;
    }

    /**
     * @param stack
     * @return enrichment [0;1]
     */
    public static double getEnrichment(ItemStack stack) {
        return getYield(stack) / ((RBMKRodItem) stack.getItem()).yield;
    }

    /**
     * @param stack
     * @return poison [0;1]
     */
    public static double getPoisonLevel(ItemStack stack) {
        return getPoison(stack) / 100D;
    }

    // START Special flux curve handling!
    // Nothing really uses this yet, though it's a really fun feature to play around with.

    // For the RBMK handler to see if the rod is special.
    public boolean specialFluxCurve = false;

    public RBMKRodItem setFluxCurve(boolean bool) {
        specialFluxCurve = bool;
        return this;
    }

    /** Double 1: Flux ratio in.
     * Double 2: Depletion value.
     * Return double: Output flux ratio.
     **/
    BiFunction<Double, Double, Double> ratioCurve;

    /** Double 1: Flux quantity in. <br>
     * Double 2: Flux ratio in. <br>
     * Return double: Output flux quantity.
     **/
    BiFunction<Double, Double, Double> fluxCurve;

    public RBMKRodItem setOutputRatioCurve(Function<Double, Double> func) {
        this.ratioCurve = (fluxRatioIn, depletion) -> func.apply(fluxRatioIn) * 1.0D;
        return this;
    }

    public RBMKRodItem setDepletionOutputRatioCurve(BiFunction<Double, Double, Double> func) {
        this.ratioCurve = func;
        return this;
    }

    public RBMKRodItem setOutputFluxCurve(BiFunction<Double, Double, Double> func) {
        this.fluxCurve = func;
        return this;
    }

    public double fluxRatioOut(double fluxRatioIn, double depletion) {
        return Mth.clamp(ratioCurve.apply(fluxRatioIn, depletion), 0, 1);
    }

    public double fluxFromRatio(double quantity, double ratio) {
        return fluxCurve.apply(quantity, ratio);
    }

    // END Special flux curve handling.

    // Original addInformation (:446-514), regular branch (:475-497). Every line is a translatable component rather than I18nUtil text,
    // which resolves to a placeholder on a dedicated server.
    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> tooltipComponents, TooltipFlag tooltipFlag) {

        if(pellet != null) tooltipComponents.add(Component.translatable(pellet.getFullNameKey()).withStyle(ChatFormatting.ITALIC));

        if(getHullHeat(stack) >= 50 || getCoreHeat(stack) >= 50) {
            tooltipComponents.add(Component.translatable("desc.item.wasteCooling").withStyle(ChatFormatting.GOLD));
        }

        if(selfRate > 0 || this.function == EnumBurnFunc.SIGMOID) {
            tooltipComponents.add(Component.translatable("trait.rbmk.source").withStyle(ChatFormatting.RED));
        }

        tooltipComponents.add(Component.translatable("trait.rbmk.depletion", ((int)(((yield - getYield(stack)) / yield) * 100000D)) / 1000D + "%").withStyle(ChatFormatting.GREEN));
        tooltipComponents.add(Component.translatable("trait.rbmk.xenon", ((int)(getPoison(stack) * 1000D) / 1000D) + "%").withStyle(ChatFormatting.DARK_PURPLE));
        tooltipComponents.add(Component.translatable("trait.rbmk.splitsWith", Component.translatable(nType.unlocalized)).withStyle(ChatFormatting.BLUE));
        tooltipComponents.add(Component.translatable("trait.rbmk.splitsInto", Component.translatable(rType.unlocalized)).withStyle(ChatFormatting.BLUE));
        tooltipComponents.add(Component.translatable("trait.rbmk.fluxFunc", getFuncDescription(stack).withStyle(ChatFormatting.WHITE)).withStyle(ChatFormatting.YELLOW));
        tooltipComponents.add(Component.translatable("trait.rbmk.funcType", this.function.getTitle()).withStyle(ChatFormatting.YELLOW));
        tooltipComponents.add(Component.translatable("trait.rbmk.xenonGen", Component.literal("x * " + xGen).withStyle(ChatFormatting.WHITE)).withStyle(ChatFormatting.YELLOW));
        tooltipComponents.add(Component.translatable("trait.rbmk.xenonBurn", Component.literal("x² / " + xBurn).withStyle(ChatFormatting.WHITE)).withStyle(ChatFormatting.YELLOW));
        tooltipComponents.add(Component.translatable("trait.rbmk.heat", heat + "°C").withStyle(ChatFormatting.GOLD));
        tooltipComponents.add(Component.translatable("trait.rbmk.diffusion", diffusion + "¹/²").withStyle(ChatFormatting.GOLD));
        tooltipComponents.add(Component.translatable("trait.rbmk.skinTemp", ((int)(getHullHeat(stack) * 10D) / 10D) + "°C").withStyle(ChatFormatting.RED));
        tooltipComponents.add(Component.translatable("trait.rbmk.coreTemp", ((int)(getCoreHeat(stack) * 10D) / 10D) + "°C").withStyle(ChatFormatting.RED));
        tooltipComponents.add(Component.translatable("trait.rbmk.melt", meltingPoint + "°C").withStyle(ChatFormatting.DARK_RED));

        super.appendHoverText(stack, context, tooltipComponents, tooltipFlag);
    }

    /*  __    __   ____     ________
     * |  \  |  | |  __ \  |__    __|
     * |   \ |  | | |__| |    |  |
     * |  |\\|  | |  __ <     |  |
     * |  | \   | | |__| |    |  |
     * |__|  \__| |_____/     |__|
     */

    public static final String KEY_YIELD = "yield";
    public static final String KEY_XENON = "xenon";
    public static final String KEY_CORE = "core";
    public static final String KEY_HULL = "hull";

    public static void setYield(ItemStack stack, double yield) {
        setDouble(stack, KEY_YIELD, yield);
    }

    public static double getYield(ItemStack stack) {

        if(stack.getItem() instanceof RBMKRodItem) {
            return getDouble(stack, KEY_YIELD);
        }

        return 0;
    }

    public static void setPoison(ItemStack stack, double xenon) {
        setDouble(stack, KEY_XENON, xenon);
    }

    public static double getPoison(ItemStack stack) {
        return getDouble(stack, KEY_XENON);
    }

    public static void setCoreHeat(ItemStack stack, double heat) {
        setDouble(stack, KEY_CORE, heat);
    }

    public static double getCoreHeat(ItemStack stack) {
        return getDouble(stack, KEY_CORE);
    }

    public static void setHullHeat(ItemStack stack, double heat) {
        setDouble(stack, KEY_HULL, heat);
    }

    public static double getHullHeat(ItemStack stack) {
        return getDouble(stack, KEY_HULL);
    }

    // Original showDurabilityBar/getDurabilityForDisplay (:561-569): the bar shows the depletion, 1 - enrichment.
    @Override
    public boolean isBarVisible(ItemStack stack) {
        return 1D - getEnrichment(stack) > 0D;
    }

    @Override
    public int getBarWidth(ItemStack stack) {
        double health = Mth.clamp(1D - getEnrichment(stack), 0D, 1D);
        return Math.round(13F - (float) health * 13F);
    }

    // The 1.7.10 RenderItem blend from green to red, as the original drew it; ZirnoxRodItem uses the vanilla 1.21 hue instead.
    @Override
    public int getBarColor(ItemStack stack) {
        double health = Mth.clamp(1D - getEnrichment(stack), 0D, 1D);
        int k = (int) Math.round(255.0D - health * 255.0D);
        return (255 - k) << 16 | k << 8;
    }

    /**
     * Original setDouble (:571-577). Before the first write the original filled in every default (setNBTDefaults, :591-597); NEO puts
     * the default of each key that is still missing, then the value. Only the server-side burn, updateHeat and provideHeat callers write.
     */
    public static void setDouble(ItemStack stack, String key, double value) {

        CompoundTag tag = TagsUtil.getCustomData(stack);

        for(String k : new String[] {KEY_YIELD, KEY_XENON, KEY_CORE, KEY_HULL}) {
            if(!tag.contains(k, Tag.TAG_ANY_NUMERIC)) tag.putDouble(k, getDefault(stack, k));
        }

        tag.putDouble(key, value);
        TagsUtil.putCustomData(stack, tag);
    }

    /**
     * Original getDouble (:579-585). A missing key reads as its setNBTDefaults default and the read never writes, so tooltips, the
     * durability bar and the hazard modifiers leave the stack alone. The original applied the defaults only to a stack without any tag
     * (an existing tag with a missing key read 0); NEO defaults each key on its own.
     */
    public static double getDouble(ItemStack stack, String key) {

        CompoundTag tag = TagsUtil.getCustomData(stack);

        if(tag.contains(key, Tag.TAG_ANY_NUMERIC)) return tag.getDouble(key);

        return getDefault(stack, key);
    }

    /** Original setNBTDefaults (:591-597): the item's yield, 20 °C core and hull, no xenon. */
    private static double getDefault(ItemStack stack, String key) {
        return switch(key) {
            case KEY_YIELD -> stack.getItem() instanceof RBMKRodItem rod ? rod.yield : 0D;
            case KEY_CORE, KEY_HULL -> 20.0D;
            default -> 0D;
        };
    }

    // The original onCreated (:599-602) wrote the defaults when the rod was crafted. NEO writes nothing on crafting; a fresh rod reads
    // the defaults and the server writes the full state on the first burn or updateHeat.
}
