# Ejecutar con mediaPlanR instalado: Rscript tests/check_canex_R.R
library(mediaPlanR)
check <- function(p, k, q, d, expected, tol=1e-10) {
  r <- suppressWarnings(calc_canex(data.frame(k=k, R1=p, R2=ifelse(k==1,p,2*p-q)), d))
  stopifnot(length(r$distribution$probability)==length(expected),
            max(abs(r$distribution$probability-expected)) < tol)
}
check(c(.3,.25), c(1,1), c(NA,NA), matrix(c(.3,.1,.1,.25),2), c(.55,.35,.1))
check(c(.3,.2), c(3,2), c(.15,.08), matrix(c(.3,.04,.04,.2),2), c(.29221281406744137,.30859602194149893,.2392132788149875,.12999523499906987,.026921535453694929,.0030611147233074103))
cat('Fixtures CanEx correctos\n')
