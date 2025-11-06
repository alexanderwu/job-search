from functools import reduce

import polars as pl
import polars.selectors as cs

################################################################################
## Polars functions
################################################################################

def reduce_list(list_list) -> list:
    uniq_set = reduce(lambda x, y: x | y, [set(x) for x in list_list if x is not None], set())
    uniq_list = sorted(uniq_set)
    return uniq_list

def pl_remove(input_column, *items) -> pl.Expr:
    pl_col = input_column
    if isinstance(input_column, str):
        pl_col = pl.col(input_column)
    return pl_col.list.eval(pl.element().filter(~pl.element().is_in(items)))

def pl_reduce_list(input_column: str | pl.Expr) -> pl.Expr:
    """Usage: pl_col.pipe(pl_reduce_list)"""
    pl_col = input_column
    if isinstance(input_column, str):
        pl_col = pl.col(input_column)
    return pl_col.drop_nulls().map_batches(reduce_list, returns_scalar=True)

def pl_enum_min(input_column: str | pl.Expr, pl_enum=None) -> pl.Expr:
    pl_col = input_column
    if isinstance(input_column, str):
        pl_col = pl.col(input_column)
    return pl_col.cast(pl.Int8).min().cast(pl_enum)

def pl_enum_max(input_column: str | pl.Expr, pl_enum=None) -> pl.Expr:
    pl_col = input_column
    if isinstance(input_column, str):
        pl_col = pl.col(input_column)
    return pl_col.cast(pl.Int8).max().cast(pl_enum)

def pl_cast_enum(input_column: str | pl.Expr, pl_enum: pl.Enum):
    pl_col = input_column
    if isinstance(input_column, str):
        pl_col = pl.col(input_column)
    enum2index = {k: v for v, k in enumerate(pl_enum.categories)}
    return pl_col.replace(enum2index).cast(pl.Int8).cast(pl_enum)

def convert_enums(pl_df: pl.DataFrame, columns: str | list | None = None, cutoff=32, sort=True, return_enums=False) -> dict | pl.DataFrame:
    if columns is None:
        columns = pl_df.select(cs.string() | cs.enum()).columns
    elif isinstance(columns, str):
        columns = [columns,]
    if sort:
        col2enum = {col: pl.Enum(list(pl_df[col].unique().sort()))
                    for col in columns if pl_df[col].n_unique() < cutoff}
    else:
        col2enum = {col: pl.Enum(list(pl_df[col].unique(maintain_order=True)))
                    for col in columns if pl_df[col].n_unique() < cutoff}
    if return_enums:
        return col2enum
    return pl_df.with_columns(pl.col(col).pipe(pl_cast_enum, col2enum[col]) for col in col2enum)
