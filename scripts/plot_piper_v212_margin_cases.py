"""Plot actual observed future margins and frozen scalar window-minimum forecasts."""
import argparse
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Refusing to overwrite figure')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    data=json.loads(a.cases.read_text());cases=data['cases']
    fig,axes=plt.subplots(1,len(cases),figsize=(14,4.8),sharey=True)
    for ax,case in zip(axes,cases):
        w=case['window'];xs=w['relative_times_s'];ys=[v*1000 for v in w['actual_margin_trace_m']]
        ax.plot(xs,ys,color='#176b9a',lw=1.8,label='Actual margin: 20 ms')
        ax.scatter(xs[::5],ys[::5],color='#17222c',s=14,zorder=3,label='Actual samples: 100 ms')
        for name,color,label in [('full_history_linear_residual','#c66c18','Linear forecast of window minimum'),
                                 ('history_gru','#963b68','GRU forecast of window minimum')]:
            pred=next(r for r in case['predictions'] if r['predictor']==name)
            ax.axhline(pred['predicted_margin_m']*1000,color=color,ls='--',lw=1.5,label=label)
        ax.axhline(0.,color='#777777',ls=':',lw=1.,label='Original 35 mm clearance boundary')
        d=case['decomposition'];chosen='linear' if case['selected_predictor'].startswith('full_') else 'GRU'
        ax.set_title(f"{w['episode_id']} | t = {w['query_time_s']:.1f}s\nSelected {chosen} error: {d['prediction_error_dense_m']*1000:.2f} mm",fontsize=10)
        ax.text(.03,.05,f"True 100/20 ms minimum gap: {d['coarse_optimistic_gap_m']*1000:.2f} mm",transform=ax.transAxes,fontsize=8.5)
        ax.set_xlabel('Time after query [s]');ax.grid(alpha=.2);ax.set_xlim(0,1);ax.set_ylim(-1,46)
    axes[0].set_ylabel('Arm-base clearance margin above 35 mm [mm]')
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.075),ncol=3,frameon=False,fontsize=8.5)
    fig.suptitle('Frozen margin forecasts and retrospective actual-state traces',fontsize=13)
    fig.text(.5,.025,'Exposed development cases selected after observing errors. Horizontal forecasts are scalar minima, not trajectories. No safety guarantee.',ha='center',fontsize=8.5)
    fig.subplots_adjust(top=.77,bottom=.28,left=.065,right=.985,wspace=.12)
    a.output.parent.mkdir(parents=True,exist_ok=True);fig.savefig(a.output,dpi=180);plt.close(fig)


if __name__=='__main__':main()
