import datetime
import os
from typing import Dict, List
import dynex
import dimod
from dynex import DynexConfig, ComputeBackend

# ====================== 基础八字计算（纯Python，无额外依赖） ======================
HEAVENLY_STEMS = "甲乙丙丁戊己庚辛壬癸"
EARTHLY_BRANCHES = "子丑寅卯辰巳午未申酉戌亥"

def get_ganzhi_year(year: int) -> str:
    stem = (year - 4) % 10
    branch = (year - 4) % 12
    return HEAVENLY_STEMS[stem] + EARTHLY_BRANCHES[branch]

def get_ganzhi_month(year: int, month: int, day: int) -> str:
    # 简化版（实际生产建议用 sxtwl 库更准，这里够演示）
    base = (year - 4) % 10 * 2 + (month - 1)
    stem = base % 10
    branch = (base + 2) % 12   # 寅月起
    return HEAVENLY_STEMS[stem] + EARTHLY_BRANCHES[branch]

def get_ganzhi_day(year: int, month: int, day: int) -> str:
    # 简化公式（实际可用万年历或 sxtwl）
    ref = datetime.date(1900, 1, 1)  # 甲子日参考
    delta = (datetime.date(year, month, day) - ref).days
    stem = delta % 10
    branch = delta % 12
    return HEAVENLY_STEMS[stem] + EARTHLY_BRANCHES[branch]

def get_ganzhi_hour(hour: int) -> str:
    branch_idx = (hour + 1) // 2 % 12
    # 时干根据日干推，这里简化固定（实际应根据日干）
    stem_idx = (branch_idx * 2) % 10
    return HEAVENLY_STEMS[stem_idx] + EARTHLY_BRANCHES[branch_idx]

# ====================== Dynex 运势采样模型 ======================
def create_fortune_bqm(day_master: str, current_pillar: str) -> dimod.BinaryQuadraticModel:
    """
    把五方面运势建模成 5 个二元变量 (0=差, 1=好)
    线性项 + 二次项体现八字五行生克（简单规则）
    """
    vars = ['career', 'wealth', 'health', 'love', 'study']
    bqm = dimod.BinaryQuadraticModel('BINARY')
    
    # 基础能量（日主影响）
    dm_idx = HEAVENLY_STEMS.find(day_master[0])
    for i, v in enumerate(vars):
        bqm.add_variable(v)
        bqm.add_linear(v, -0.5 if i % 2 == dm_idx % 2 else 0.8)  # 日主同类加分
    
    # 当前时柱冲突/相合简单规则
    if current_pillar[1] in "子午卯酉":      # 冲
        bqm.add_linear('health', 1.2)
        bqm.add_linear('love', 1.5)
    elif current_pillar[0] == day_master[0]:  # 比和
        bqm.add_linear('career', -1.0)
        bqm.add_linear('wealth', -0.8)
    
    # 部分二次交互（示范）
    bqm.add_quadratic('career', 'wealth', -0.3)   # 事业好→财运好
    bqm.add_quadratic('health', 'love', -0.4)
    
    return bqm

def predict_minute_fortune(day_master: str, current_pillar: str, num_reads: int = 20) -> Dict:
    bqm = create_fortune_bqm(day_master, current_pillar)
    model = dynex.BQM(bqm)
    
    config = DynexConfig(
        compute_backend=ComputeBackend.CPU,   # 演示用 CPU（快且免费），生产可改 QPU
        default_timeout=30.0,
        use_notebook_output=False
    )
    
    sampler = dynex.DynexSampler(model, config=config)
    sampleset = sampler.sample(num_reads=num_reads, annealing_time=200)
    
    # 取最低能量样本
    best = sampleset.first
    state = best.sample
    energy = best.energy
    
    # 映射成文字
    scores = {k: "优秀" if v == 1 else "一般" for k, v in state.items()}
    total_score = int((5 - energy) / 5 * 100)   # 简单归一化 0-100
    desc = f"整体运势 {total_score} 分 | 事业{scores['career']}、财运{scores['wealth']}、健康{scores['health']}、感情{scores['love']}、学业{scores['study']}"
    
    return {
        "pillar": current_pillar,
        "total_score": total_score,
        "details": scores,
        "description": desc,
        "energy": energy
    }

# ====================== 主程序：某天每分钟运势 ======================
def daily_minute_fortune(birth_date: datetime.datetime, target_date: datetime.date, granularity: int = 1):
    """
    granularity=1 表示每分钟（1440次，演示建议先设 60 即每小时）
    """
    # 1. 计算命主日干（日主）
    birth_pillar = get_ganzhi_day(birth_date.year, birth_date.month, birth_date.day)
    day_master = birth_pillar[0]   # 日干即日主
    
    print(f"命主日干：{day_master}（八字简化版）")
    print(f"目标日期：{target_date} 每{granularity}分钟运势\n")
    
    results = []
    start = datetime.datetime.combine(target_date, datetime.time(0, 0))
    end = start + datetime.timedelta(days=1)
    current = start
    
    while current < end:
        # 当前时柱（每2小时一柱，这里用当前小时）
        hour_pillar = get_ganzhi_hour(current.hour)
        minute_key = current.strftime("%H:%M")
        
        fortune = predict_minute_fortune(day_master, hour_pillar)
        
        results.append({
            "时间": minute_key,
            **fortune
        })
        
        current += datetime.timedelta(minutes=granularity)
    
    # 输出表格
    print(f"{'时间':<6} {'时柱':<4} {'总分':<4} {'事业':<4} {'财运':<4} {'健康':<4} {'感情':<4} {'学业':<4} 描述")
    print("-" * 80)
    for r in results:
        d = r['details']
        print(f"{r['时间']:<6} {r['pillar']:<4} {r['total_score']:>3}   "
              f"{d['career']:<4} {d['wealth']:<4} {d['health']:<4} {d['love']:<4} {d['study']:<4} "
              f"{r['description']}")
    
    return results

# ====================== 示例运行 ======================
if __name__ == "__main__":
    # 改成你自己的出生日期和要算的日期
    birth = datetime.datetime(1995, 6, 15, 14, 30)      # 示例出生
    target_day = datetime.date(2026, 4, 10)             # 要算的某天
    
    # granularity=60 表示每小时一次（演示推荐，速度快）
    # 改成 1 就是真正的每分钟（会跑 1440 次，CPU 也只需几分钟）
    daily_minute_fortune(birth, target_day, granularity=60)