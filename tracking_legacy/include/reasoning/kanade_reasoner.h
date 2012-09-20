#ifndef KANADE_REASONER_H
#define KANADE_REASONER_H

#include <iterator>
#include <map>
#include <utility>
#include <vector>
#include <boost/function.hpp>
#include <ilcplex/ilocplex.h>
#include "reasoning/reasoner.h"
#include "hypotheses.h"

namespace Tracking {
class Traxel;
class HypothesesGraph;

class KanadeIlp {
 public:
  /** idxs will be assumed to lie consecutivly in the range 0 ... (n_tracklets-1) **/
  template <typename iterator>
    KanadeIlp( iterator begin_fp_cost, iterator end_fp_cost );
  ~KanadeIlp();

  size_t add_init_hypothesis(size_t idx, double cost); // initialization
  size_t add_term_hypothesis(size_t idx, double cost); // termination
  size_t add_trans_hypothesis(size_t from_idx, size_t to_idx, double cost); // translation
  size_t add_div_hypothesis(size_t from_idx, size_t to_idx1, size_t to_idx2, double cost); // division

  KanadeIlp& solve();
  size_t solution_size();
  bool hypothesis_is_active( size_t hypothesis_id );

 protected:
  size_t add_fp_hypothesis(size_t idx, double cost); // false positive

 private:
  size_t n_tracklets_;
  size_t n_hypotheses_;
  
  IloEnv env_;
  IloModel model_;
  IloObjective obj_;
  IloBoolVarArray x_;
  IloRangeArray c_;
  IloNumArray sol_;
  IloCplex cplex_;
};



class Kanade : public Reasoner {
 public:
 Kanade(boost::function<double (const Traxel&)> ini_potential,
	boost::function<double (const Traxel&)> term_potential,
	boost::function<double (const Traxel&, const Traxel&)> link_potential,
	boost::function<double (const Traxel&, const Traxel&, const Traxel&)> div_potential,
	boost::function<double (const Traxel&)> tp_potential,
	boost::function<double (const Traxel&)> fp_potential    
	)
   : ini_potential_(ini_potential),
    term_potential_(term_potential),
    link_potential_(link_potential),
    div_potential_(div_potential),
    tp_potential_(tp_potential),
    fp_potential_(fp_potential),    
    ilp_(NULL) {}
  ~Kanade();

    virtual void formulate( const HypothesesGraph& );
    virtual void infer();
    virtual void conclude( HypothesesGraph& );

 protected:
    void reset();
    Kanade& add_hypotheses( const HypothesesGraph&, const HypothesesGraph::Node& );

 private:
    // copy and assingment have to be implemented, yet
    Kanade(const Kanade&) {};
    Kanade& operator=(const Kanade&) { return *this;};

    // potential functions
    boost::function<double (const Traxel&)> ini_potential_;
    boost::function<double (const Traxel&)> term_potential_;
    boost::function<double (const Traxel&, const Traxel&)> link_potential_;
    boost::function<double (const Traxel&, const Traxel&, const Traxel&)> div_potential_;
    boost::function<double (const Traxel&)> tp_potential_;
    boost::function<double (const Traxel&)> fp_potential_;    

    // ilp related
    KanadeIlp* ilp_;
    std::map<HypothesesGraph::Node, size_t> tracklet_idx_map_;

    // hypotheses maps
    enum hyp_type {TERM, INIT, TRANS, DIV, FP};
    std::map<size_t, hyp_type> hyp2type_;
    std::map<size_t, HypothesesGraph::Node> fp2node_;
    std::map<size_t, HypothesesGraph::Arc> trans2arc_;
    std::map<size_t, std::pair<HypothesesGraph::Arc,HypothesesGraph::Arc> > div2arcs_;
};



/******************/
/* Implementation */
/******************/

 template<typename iterator>
   KanadeIlp::KanadeIlp( iterator begin, iterator end ) : n_tracklets_(distance(begin, end)), n_hypotheses_(0) {
    model_ = IloModel(env_);
    obj_ = IloMaximize( env_ );
    cplex_ = IloCplex( env_ );
    x_ = IloBoolVarArray( env_, 0);
    sol_ = IloNumArray( env_, 0);

    // 2 * n constraints: sum == 1
    c_ = IloRangeArray( env_, 2 * n_tracklets_, 1, 1);

    // for every tracklet: add a false positve hypothesis
    size_t idx = 0, hyp_idx = 0;
    for(iterator cost_it = begin; cost_it != end; ++cost_it) {
      hyp_idx = add_fp_hypothesis(idx, *cost_it);
      assert(hyp_idx == idx);
      ++idx;
    }
  }

} /* namespace Tracking */

#endif /* KANADE_REASONER_H */